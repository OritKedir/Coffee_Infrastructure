# Dataset growth benchmark

| Scale | Rows | Runs | Load (s), mean ± sample SD | MySQL peak RAM (MiB), mean | Loader peak RAM (MiB), mean | Combined sampled peak (MiB), mean | Table disk (MiB), mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| 25% | 4285968 | 3 | 180.47 ± 4.89 | 604.63 | 126.07 | 730.57 | 616.00 |
| 50% | 8571936 | 3 | 361.01 ± 17.52 | 613.50 | 134.87 | 747.67 | 1212.00 |
| 100% | 17143873 | 3 | 736.08 ± 28.95 | 623.40 | 140.57 | 763.13 | 2388.00 |

Method: deterministic nested CSV prefixes; entire FAOSTAT dataset, no coffee filter. Fresh MySQL container and data volume per run; original init.sql, no added secondary indexes. Chunk size 10,000. The project's dashboard and original database containers were stopped during the benchmark. Load timer includes ZIP/CSV reading, transformation and committed SQL inserts, excluding download, row counting, image build, server startup and validation. Docker stats is polled repeatedly (command duration plus 1 s); peaks are sampled estimates, not guaranteed instantaneous maxima. Combined peak is the maximum paired sum, not the sum of independent peaks. Disk is allocated raw_trade.ibd space after load, excluding shared MySQL files, redo/binlogs, Docker images and source ZIP. Host/VM filesystem cache is not cleared; this is not a fully cold-cache benchmark. Runs are serial on one machine, cycling 25/50/100 three times. See metadata.json for software and Docker resources.
