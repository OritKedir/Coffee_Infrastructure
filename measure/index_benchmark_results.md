# Database Index Benchmark Experiment Results

| Index Setup              | Columns               |   Run 1 (s) |   Run 2 (s) |   Run 3 (s) |   Average Time (s) | Speedup   |
|:-------------------------|:----------------------|------------:|------------:|------------:|-------------------:|:----------|
| No Index (Baseline)      | None                  |     10.0936 |      9.7867 |      9.6901 |             9.8568 | 1.0x      |
| 1 Column Index           | (item)                |      3.9742 |      1.4008 |      1.4108 |             2.2619 | 4.36x     |
| 2 Column Index           | (item, year)          |      1.3251 |      0.6029 |      0.587  |             0.8383 | 11.76x    |
| 3 Column Composite Index | (item, year, element) |      1.0154 |      0.5314 |      0.5576 |             0.7015 | 14.05x    |