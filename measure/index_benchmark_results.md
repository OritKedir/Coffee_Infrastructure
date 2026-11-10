# Database Index Benchmark Experiment Results

| Index Setup              | Columns               |   Run 1 (s) |   Run 2 (s) |   Run 3 (s) |   Average Time (s) | Speedup   |
|:-------------------------|:----------------------|------------:|------------:|------------:|-------------------:|:----------|
| No Index (Baseline)      | None                  |     25.1272 |     23.8503 |     24.2826 |            24.42   | 1.0x      |
| 1 Column Index           | (item)                |     19.8289 |     17.4083 |     17.3767 |            18.2046 | 1.34x     |
| 2 Column Index           | (item, year)          |     11.2344 |      9.229  |      9.4307 |             9.9647 | 2.45x     |
| 3 Column Composite Index | (item, year, element) |      9.793  |      8.5373 |      8.3034 |             8.8779 | 2.75x     |