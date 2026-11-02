# FAOSTAT Coffee Trade Data Specification

## 1. Source
- Dataset: FAOSTAT, Trade: Crops and livestock products, bulk download "All Data Normalized".
- FAOSTAT last update: 24 July 2026.
- ZIP size: 267 MB. Main CSV once unzipped: 2.3 GB (`Trade_CropsLivestock_E_All_Data_(Normalized).csv`).
- Companion files: `AreaCodes`, `Elements`, `Flags`, `ItemCodes` (small CSVs).
- The ZIP and the CSV are never committed. The loader downloads the data at runtime and reads the CSV in chunks.

## 2. Columns (14)
| CSV header | SQL name | SQL type | Note |
|---|---|---|---|
| Area Code | area_code | INT | |
| Area Code (M49) | area_code_m49 | VARCHAR(50) | starts with an apostrophe, e.g. `'004` (strip it) |
| Area | area | VARCHAR(255) | |
| Item Code | item_code | INT | |
| Item Code (CPC) | item_code_cpc | VARCHAR(50) | starts with an apostrophe, e.g. `'01610` (strip it) |
| Item | item | VARCHAR(255) | |
| Element Code | element_code | INT | |
| Element | element | VARCHAR(100) | |
| Year Code | year_code | INT | |
| Year | year | INT | |
| Unit | unit | VARCHAR(50) | `t` or `1000 USD` |
| Value | value | DECIMAL(15,2) | the CSV has 6 decimals |
| Flag | flag | VARCHAR(10) | can be empty |
| Note | note | TEXT | can be empty |

All fields are quoted and comma-separated.

## 3. Commodity filter
- Item Code 656 = "Coffee, green" (CPC 01610). 53,892 rows over all years, areas and elements.
- Filter on the code, not on the name: the ItemCodes file spells it "Coffee; green".
- Excluded related items: 657 roasted or decaffeinated, 658 substitutes, 659 extracts, 660 husks and skins.

## 4. Elements and units
| Element code | Element | Unit | Rows | Used |
|---|---|---|---|---|
| 5610 | Import quantity | t | 14,302 | yes |
| 5910 | Export quantity | t | 12,590 | yes |
| 5622 | Import value | 1000 USD | 14,371 | no |
| 5922 | Export value | 1000 USD | 12,629 | no |

- Filter on `element_code`, not on the name.
- Net trade = Export quantity - Import quantity (tonnes). If a country has no row for one of the two in a year, it counts as 0.

## 5. Years
- Available: 1961-2024. We use the latest 10 years: 2015-2024.
- About 940-990 rows per year for coffee (all four elements), 9,640 rows in 2015-2024.

## 6. Aggregates to filter out
- Rule: exclude a row if `area_code >= 5000` OR `area_code_m49` contains a dot.
- `area_code >= 5000` catches World (5000), the continents and `European Union (27)` (5707), which has no dot in M49.
- The dot catches the "(excluding intra-trade)" groups, including `China (excluding intra-trade)` (265) and the old EU groups (261, 266, 268, 269), which are below 5000.
- AreaCodes does not list which country belongs to which region: the "Europe" query needs its own list of European country codes.
