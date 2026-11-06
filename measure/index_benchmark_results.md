# Database Index Benchmark Experiment Results

| Index Setup              | Columns               |   Run 1 (s) |   Run 2 (s) |   Run 3 (s) |   Average Time (s) | Speedup   |
|:-------------------------|:----------------------|------------:|------------:|------------:|-------------------:|:----------|
| No Index (Baseline)      | None                  |      7.9429 |      7.4546 |      7.1587 |             7.5187 | 1.0x      |
| 1 Column Index           | (item)                |      3.0377 |      0.9654 |      0.9656 |             1.6563 | 4.54x     |
| 2 Column Index           | (item, year)          |      0.9766 |      0.357  |      0.3316 |             0.5551 | 13.55x    |
| 3 Column Composite Index | (item, year, element) |      0.4204 |      0.3556 |      0.3501 |             0.3753 | 20.03x    |