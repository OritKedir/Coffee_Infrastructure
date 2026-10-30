# Coffee_Infrastructure
Get the best coffee exporter and importer
Project Specification: Global Coffee Trade
Analysis
1. Research Question
"Which countries are the top five net exporters and top five net importers of
coffee beans in europe and inthe worldwide, and how has their net trade volume shifted over
the last 10 years?"
2. Dataset
Source: FAOSTAT (Food and Agriculture Organization of the United Nations)
Specific Dataset: Trade: Crops and Livestock Products (Normalized)
Direct Script Download Link:
https://fenixservices.fao.org/faostat/static/bulkdownloads/Trade_
CropsLivestock_E_All_Data_(Normalized).zip
Licence: Open Access 
Relational tabular schema where every row has identical attributes: AreaCode,
Area, ItemCode, Item, Element, Year, Unit, Value.
3. Database Selection (MySQL)
●
Database Engine: MySQL
4. Final Output
●
User Interface: A interactive web dashboard built with Streamlit
●
Dashboard Components:
1. Top Ranking Panel:
2. 10-Year Trajectory Panel:
3. Live Infrastructure Metrics:
5. System Architecture & Docker Packaging
The system consists of three isolated services orchestrated via Docker Compose, running with
a single command: docker compose up --build.
System Diagram
None‎
[ Public Source: FAOSTAT ]
│
▼
│ (HTTP GET direct .zip download)
┌─────────────────────────────────────────────────────────────┐
│ docker compose network │
│ │
│ ┌────────────────────────┐ ┌──────────────────┐ │
│ │ loader │ │ db │ │
│ │ Python Script │────────►│ MySQL 8.4 │ │
│ │ (Downloads, extracts, │ Rows │ (Indexed Relational│ │
│ │ runs LOAD DATA) │ │ Storage) │ │
│ └────────────────────────┘ └────────┬─────────┘ │
│ │ │
│ ┌────────────────────────┐ │ │
│ │ app │◄──(SQL Queries)──┘ │
│ │ Streamlit Dashboard │ │
│ └───────────┬────────────┘ │
└───────────────┼─────────────────────────────────────────────┘
│
│ localhost:8501
▼
[ User Web Browser ]
Service Roles & Data Flow
2. db (MySQL 8.4):
3.
loader (Python):
4. app (Streamlit):