"""Run from the repository root. Host requirements: Python standard library + Docker."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import statistics
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def docker(*args, input=None, check=True, timeout=None):
    result = subprocess.run(['docker', *map(str, args)], input=input, text=True,
                            encoding='utf-8', errors='replace', capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'Docker command failed: {result.stderr.strip()}\n{result.stdout[-3000:]}')
    return result.stdout.strip()


def memory_mib(value):
    number, unit = re.fullmatch(r'([\d.]+)\s*([A-Za-z]+)', value.split('/')[0].strip()).groups()
    factors = {'B': 1, 'kB': 1000, 'KB': 1000, 'MB': 1000**2, 'GB': 1000**3,
               'TB': 1000**4, 'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4}
    return float(number) * factors[unit] / 1024**2


def save_table(path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-test', action='store_true', help='One 10,000-row validation run')
    args = parser.parse_args()
    for relative in ['data/faostat_trade.zip', 'loader/Dockerfile', 'loader/load_data.py', 'sql/init.sql']:
        if not (ROOT / relative).is_file():
            raise FileNotFoundError(ROOT / relative)
    if 'MAX_ROWS' not in (ROOT / 'loader/load_data.py').read_text(encoding='utf-8-sig'):
        raise RuntimeError('Install the supplied loader/load_data.py first.')
    docker('info')
    token = secrets.token_hex(5)
    network = 'coffee-growth-' + token
    image = 'coffee-growth-loader:' + token
    password = secrets.token_hex(16)
    folder = ROOT / 'measure' / ('growth_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + token)
    folder.mkdir(parents=True)
    print('Building the benchmark loader...', flush=True)
    docker('build', '-t', image, ROOT / 'loader')
    # Pin this invocation to the local MySQL image used by the project.
    mysql_image = docker('image', 'inspect', 'mysql:8.4', '--format', '{{.Id}}')
    data_mount = f'type=bind,source={ROOT / "data"},target=/data,readonly'
    print('Counting CSV rows once (excluded from benchmark time)...', flush=True)
    count_code = "from zipfile import ZipFile; import pandas as pd; z=ZipFile('/data/faostat_trade.zip'); names=[n for n in z.namelist() if n.endswith('(Normalized).csv')]; assert len(names)==1; print(sum(len(c) for c in pd.read_csv(z.open(names[0]),chunksize=50000,encoding='latin-1')))"
    total = int(docker('run', '--rm', '--mount', data_mount, image, 'python', '-c', count_code).splitlines()[-1])
    if total < 4:
        raise RuntimeError('Dataset is too small')
    print(f'Full dataset: {total:,} rows', flush=True)
    metadata = {'utc': datetime.now(timezone.utc).isoformat(), 'total_rows': total,
                'mysql_image': mysql_image, 'smoke_test': args.smoke_test,
                'docker_version': docker('version', '--format', '{{json .}}'),
                'docker_resources': docker('info', '--format', '{{json .NCPU}} CPUs, {{json .MemTotal}} bytes RAM'),
                'schema': (ROOT / 'sql/init.sql').read_text(encoding='utf-8-sig'),
                'packages': docker('run', '--rm', image, 'pip', 'freeze')}
    (folder / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    jobs = [(0, 1, min(10000, total))] if args.smoke_test else [
        (pct, repeat, total * pct // 100) for repeat in range(1, 4) for pct in (25, 50, 100)]
    results = []
    docker('network', 'create', network)
    try:
        for pct, repeat, target in jobs:
            db, loader = network + '-db', network + '-loader'
            stop = threading.Event()
            samples, monitor_errors = [], []
            thread = None
            label = f'{pct}pct_run{repeat}'
            print(f'\n{label}: loading {target:,} rows into a fresh MySQL instance', flush=True)
            def sql(statement):
                return docker('exec', '-i', '-e', 'MYSQL_PWD=' + password, db,
                              'mysql', '-uroot', '-N', '-B', input=statement)
            def monitor():
                while not stop.is_set():
                    try:
                        raw = docker('stats', '--no-stream', '--format', '{{json .}}', db, loader, timeout=30)
                        values = {v['Name']: memory_mib(v['MemUsage']) for v in map(json.loads, raw.splitlines())}
                        if db in values and loader in values:
                            samples.append({'elapsed_s': time.monotonic() - start,
                                            'mysql_mib': values[db], 'loader_mib': values[loader],
                                            'combined_mib': values[db] + values[loader]})
                    except Exception as exc:
                        monitor_errors.append(str(exc))
                    stop.wait(1)
            try:
                docker('run', '-d', '--name', db, '--network', network,
                       '-e', 'MYSQL_ROOT_PASSWORD=' + password, '-e', 'MYSQL_ROOT_HOST=%',
                       '--mount', 'type=volume,target=/var/lib/mysql', mysql_image)
                deadline = time.monotonic() + 300
                while True:
                    try:
                        # TCP checks the final server, not the entrypoint's temporary socket server.
                        docker('exec', '-e', 'MYSQL_PWD=' + password, db, 'mysql',
                               '-h127.0.0.1', '-uroot', '-N', '-e', 'SELECT 1;', timeout=10)
                        break
                    except Exception:
                        if time.monotonic() > deadline:
                            raise RuntimeError('MySQL did not become ready: ' + docker('logs', db, check=False))
                        time.sleep(2)
                sql(metadata['schema'])
                if sql('SELECT COUNT(*) FROM coffee_trade.raw_trade;') != '0':
                    raise RuntimeError('Benchmark table is not empty')
                docker('run', '-d', '--name', loader, '--network', network,
                       '--mount', data_mount, '-e', 'LOCAL_DATA_ONLY=1', '-e', 'DATA_DIR=/data',
                       '-e', 'MAX_ROWS=' + str(target),
                       '-e', f'DATABASE_URL=mysql+pymysql://root:{password}@{db}:3306/coffee_trade',
                       image, 'python', '-c', 'import time; time.sleep(604800)')
                start = time.monotonic()
                thread = threading.Thread(target=monitor)
                thread.start()
                # Keep the container alive so its final RAM sample remains available.
                log_path = folder / (label + '.log')
                with log_path.open('w', encoding='utf-8') as log:
                    process = subprocess.Popen(['docker', 'exec', loader, 'python', '-u', '/app/load_data.py'],
                                               stdout=log, stderr=subprocess.STDOUT)
                    try:
                        while process.poll() is None:
                            time.sleep(1)
                    finally:
                        if process.poll() is None:
                            process.terminate()
                            process.wait()
                if process.returncode:
                    raise RuntimeError(f'Loader failed; see {log_path}')
                stop.set()
                thread.join()
                if not samples or monitor_errors:
                    raise RuntimeError('RAM monitoring incomplete: ' + '; '.join(monitor_errors))
                text = log_path.read_text(encoding='utf-8')
                measurement = json.loads(next(line.split('=', 1)[1] for line in text.splitlines()
                                              if line.startswith('BENCHMARK_RESULT=')))
                actual = int(sql('SELECT COUNT(*) FROM coffee_trade.raw_trade;'))
                if actual != target or measurement['rows'] != target:
                    raise RuntimeError(f'Row count mismatch: expected {target}, actual {actual}')
                # du measures allocated filesystem blocks of the table tablespace, not the ZIP.
                sql('FLUSH TABLES coffee_trade.raw_trade FOR EXPORT;')
                kib = int(docker('exec', db, 'du', '-k', '/var/lib/mysql/coffee_trade/raw_trade.ibd').split()[0])
                row = {'scale_pct': pct, 'run': repeat, 'rows': actual,
                       'load_seconds': measurement['load_seconds'],
                       'mysql_peak_mib': max(s['mysql_mib'] for s in samples),
                       'loader_peak_mib': max(s['loader_mib'] for s in samples),
                       'combined_peak_mib': max(s['combined_mib'] for s in samples),
                       'table_disk_mib': kib / 1024, 'ram_samples': len(samples)}
                results.append(row)
                save_table(folder / (label + '_ram.csv'), samples)
                save_table(folder / 'growth_runs.csv', results)
                print(f'Done: {row["load_seconds"]:.1f} s; {row["table_disk_mib"]:.1f} MiB disk', flush=True)
            finally:
                stop.set()
                if thread:
                    thread.join()
                # Only random names created by THIS invocation are removed.
                docker('rm', '-f', '-v', loader, check=False)
                docker('rm', '-f', '-v', db, check=False)
        if not args.smoke_test:
            lines = ['# Dataset growth benchmark', '',
                     '| Scale | Rows | Runs | Load (s), mean ± sample SD | MySQL peak RAM (MiB), mean | Loader peak RAM (MiB), mean | Combined sampled peak (MiB), mean | Table disk (MiB), mean |',
                     '|---|---:|---:|---:|---:|---:|---:|---:|']
            for pct in (25, 50, 100):
                group = [r for r in results if r['scale_pct'] == pct]
                mean = lambda key: statistics.mean(r[key] for r in group)
                sd = statistics.stdev(r['load_seconds'] for r in group)
                lines.append(f'| {pct}% | {group[0]["rows"]} | 3 | {mean("load_seconds"):.2f} ± {sd:.2f} | {mean("mysql_peak_mib"):.2f} | {mean("loader_peak_mib"):.2f} | {mean("combined_peak_mib"):.2f} | {mean("table_disk_mib"):.2f} |')
            lines += ['', 'Method: deterministic nested CSV prefixes; entire FAOSTAT dataset, no coffee filter. Fresh MySQL container and data volume per run; original init.sql, no added secondary indexes. Chunk size 10,000. Load timer includes ZIP/CSV reading, transformation and committed SQL inserts, excluding download, row counting, image build, server startup and validation. Docker stats is polled repeatedly (command duration plus 1 s); peaks are sampled estimates, not guaranteed instantaneous maxima. Combined peak is the maximum paired sum, not the sum of independent peaks. Disk is allocated raw_trade.ibd space after load, excluding shared MySQL files, redo/binlogs, Docker images and source ZIP. Host/VM filesystem cache is not cleared; this is not a fully cold-cache benchmark. Runs are serial on one machine, cycling 25/50/100 three times. See metadata.json for software and Docker resources.']
            (folder / 'growth_summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print('\nCOMPLETE. Results: ' + str(folder), flush=True)
    finally:
        docker('network', 'rm', network, check=False)
        docker('image', 'rm', image, check=False)


if __name__ == '__main__':
    main()
