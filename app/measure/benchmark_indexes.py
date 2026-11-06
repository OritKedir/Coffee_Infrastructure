import os
import time
import pandas as pd
import pymysql

from pathlib import Path


def load_env_file():
    """Load the project's .env (searched upward from this file) into os.environ.
    Existing environment variables win, so values can still be overridden."""
    for folder in Path(__file__).resolve().parents:
        env_path = folder / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return env_path
    return None


load_env_file()

# 'db' only resolves inside the docker network; on a host machine use localhost.
_in_docker = Path("/.dockerenv").exists()
_host = os.getenv("MYSQL_HOST", "localhost")
if _host == "db" and not _in_docker:
    _host = "localhost"

# Database connection credentials (read from the project's .env)
DB_HOST = _host
DB_USER = os.getenv("MYSQL_USER", "team_user")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "secret")
DB_NAME = os.getenv("MYSQL_DATABASE", "coffee_trade")
DB_PORT = int(os.getenv("MYSQL_PORT", 3306))

# The analytical query to measure (Federico's net trade aggregation)
BENCHMARK_QUERY = """
SELECT 
    area,
    year,
    SUM(CASE WHEN element = 'Export Quantity' THEN value ELSE 0 END) AS exports,
    SUM(CASE WHEN element = 'Import Quantity' THEN value ELSE 0 END) AS imports,
    SUM(CASE WHEN element = 'Export Quantity' THEN value ELSE 0 END) - 
    SUM(CASE WHEN element = 'Import Quantity' THEN value ELSE 0 END) AS net_trade
FROM raw_trade
WHERE item = 'Coffee, green'
  AND year >= 2013
GROUP BY area, yeargit 
ORDER BY net_trade DESC;
"""

# Experiment index definitions
EXPERIMENTS = [
    {
        "name": "No Index (Baseline)",
        "columns": None
    },
    {
        "name": "1 Column Index",
        "columns": "(item)"
    },
    {
        "name": "2 Column Index",
        "columns": "(item, year)"
    },
    {
        "name": "3 Column Composite Index",
        "columns": "(item, year, element)"
    }
]

INDEX_NAME = "idx_experiment"


def drop_experiment_index(cursor):
    """Drops the experiment index if it already exists."""
    cursor.execute(f"""
        SELECT COUNT(1) 
        FROM information_schema.statistics 
        WHERE table_schema = '{DB_NAME}' 
          AND table_name = 'raw_trade' 
          AND index_name = '{INDEX_NAME}';
    """)
    if cursor.fetchone()[0] > 0:
        cursor.execute(f"ALTER TABLE raw_trade DROP INDEX {INDEX_NAME};")


def measure_query(cursor, query):
    """Executes the query and returns execution latency using time.perf_counter()."""
    start_time = time.perf_counter()
    cursor.execute(query)
    cursor.fetchall()  # Fetch full result set from buffer
    return time.perf_counter() - start_time


def run_benchmark():
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        autocommit=True
    )

    results = []
    baseline_avg = None

    try:
        with connection.cursor() as cursor:
            print("=" * 65)
            print("🚀 Starting Database Index Benchmark Experiment (3 runs each)")
            print("=" * 65)

            for exp in EXPERIMENTS:
                print(f"\nConfiguration: {exp['name']}")

                # 1. Reset / Apply target index
                drop_experiment_index(cursor)
                if exp["columns"]:
                    print(f"Creating index: CREATE INDEX {INDEX_NAME} ON raw_trade{exp['columns']}...")
                    cursor.execute(f"CREATE INDEX {INDEX_NAME} ON raw_trade {exp['columns']};")
                else:
                    print("Running on unindexed table scan...")

                # 2. Run query 3 times
                runs = []
                for i in range(1, 4):
                    duration = measure_query(cursor, BENCHMARK_QUERY)
                    runs.append(duration)
                    print(f"  Run {i}: {duration:.4f} seconds")

                avg_time = sum(runs) / len(runs)

                # Set baseline using 'No Index'
                if baseline_avg is None:
                    baseline_avg = avg_time
                    speedup = 1.0
                else:
                    speedup = baseline_avg / avg_time if avg_time > 0 else 0.0

                print(f"  -> Average: {avg_time:.4f} s | Speedup: {speedup:.2f}x")

                results.append({
                    "Index Setup": exp["name"],
                    "Columns": exp["columns"] if exp["columns"] else "None",
                    "Run 1 (s)": round(runs[0], 4),
                    "Run 2 (s)": round(runs[1], 4),
                    "Run 3 (s)": round(runs[2], 4),
                    "Average Time (s)": round(avg_time, 4),
                    "Speedup": f"{round(speedup, 2)}x"
                })

            # Cleanup index at end of experiment
            drop_experiment_index(cursor)

    finally:
        connection.close()

    # 3. Format and save results automatically
    df = pd.DataFrame(results)
    
    os.makedirs("measure", exist_ok=True)
    csv_file = "measure/index_benchmark_results.csv"
    md_file = "measure/index_benchmark_results.md"

    df.to_csv(csv_file, index=False)
    with open(md_file, "w") as f:
        f.write("# Database Index Benchmark Experiment Results\n\n")
        f.write(df.to_markdown(index=False))

    print("\n" + "=" * 65)
    print("📋 SUMMARY OF RESULTS:")
    print("=" * 65)
    print(df.to_string(index=False))
    print(f"\nSaved results to:\n - {csv_file}\n - {md_file}")


if __name__ == "__main__":
    run_benchmark()