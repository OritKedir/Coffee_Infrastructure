# Global Coffee Trade Analysis Infrastructure

A containerized data infrastructure pipeline built to ingest, index, and analyze international coffee trade balances over a 10-year period using FAOSTAT bulk data, MySQL 8.4, and Streamlit.

---

## 1. Project Specification

* **Research Question**  
  > Which countries are the top five net exporters and top five net importers of coffee beans globally and in Europe, and how has their net trade volume shifted over the last 10 years?

* **Dataset Source & Access**  
  * **Source:** [FAOSTAT](https://www.fao.org/faostat/) (Food and Agriculture Organization of the United Nations)  
  * **Dataset:** *Trade: Crops and Livestock Products (Normalized)*  
  * **Direct Script Download Link:**  
    `https://fenixservices.fao.org/faostat/static/bulkdownloads/Trade_CropsLivestock_E_All_Data_(Normalized).zip`  
  * **License:** Open Access ([CC BY-NC-SA 3.0 IGO](https://creativecommons.org/licenses/by-nc-sa/3.0/igo/))  
  * **Schema Format:** Normalized tabular CSV with fixed attributes (`AreaCode`, `Area`, `ItemCode`, `Item`, `Element`, `Year`, `Unit`, `Value`).

* **Database Selection: MySQL 8.4**  
  * **Relational Structure:** Fits the rigid schema across millions of standardized trade observation rows.  
  * **Fast Bulk Ingestion:** Utilizes `LOAD DATA LOCAL INFILE` to stream large CSV files directly to disk without memory bottlenecks.  
  * **Targeted Indexing:** Composite B-tree index on `(ItemCode, Element, Year)` accelerates compute times for trade balance aggregations.

* **Data Processing Pipeline**  
  1. **Automated ETL:** The `loader` service downloads and unpacks the bulk archive into MySQL.  
  2. **Aggregation Logic:** SQL queries compute net balances:  
     $$\text{Net Trade Volume} = \sum(\text{Export Quantity}) - \sum(\text{Import Quantity})$$  
  3. **Ranking & Filtering:** Partitions records to isolate Europe and global rankings over a continuous 10-year window.

* **Final Output Interface**  
  * **Streamlit Dashboard:** Interactive web app exposed at `http://localhost:8501`.  
  * **Visual Panels:** Top-5 rankings, 10-year historical trajectory charts, and query latency measurements.

---

## 2. System Architecture

```text
                      [ Outside Environment ]
                                 │
                                 │  FAOSTAT Bulk Data (.zip)
                                 │  (HTTP GET direct download)
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     docker-compose network                      │
│                                                                 │
│   ┌───────────────┐     LOAD DATA LOCAL     ┌───────────────┐   │
│   │    loader     │ ──────────────────────> │      db       │   │
│   │ (Python ETL)  │                         │  (MySQL 8.4)  │   │
│   └───────────────┘                         └───────┬───────┘   │
│                                                     │           │
│                                                     │ SQL       │
│                                                     │ Queries   │
│                                                     ▼           │
│   ┌───────────────┐                         ┌───────────────┐   │
│   │    Browser    │ <────── localhost:8501 ─ │      app      │   │
│   │   (Client)    │                         │  (Streamlit)  │   │
│   └───────────────┘                         └───────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```