# Cooperative Member Data ETL Pipeline (Python · Pandas · SQLite)

A small end-to-end **ETL (Extract → Transform → Load)** pipeline that migrates
cooperative **member, savings, and loan** data from messy CSV/Excel source
files into a clean SQLite database, and produces a **reconciliation report**.

It re-implements, in Python and Pandas, the same data-migration and
data-quality pattern I work with on Microsoft SQL Server: source-to-target
mapping, cleaning, validation, duplicate detection, referential-integrity
checks, and source-vs-target balance reconciliation.

## What the pipeline does

| Stage | What happens |
|-------|--------------|
| **1. Extract** | Reads `members.csv`, `savings.xlsx`, `loans.csv` into pandas DataFrames |
| **2. Clean** | Trims spaces, standardises text casing, parses mixed-format dates |
| **3. Validate** | Removes duplicate members, rejects orphan accounts (bad member references) and negative balances |
| **4. Load** | Writes the clean tables into a SQLite database (`data/target/cooperative.db`) |
| **5. Reconcile** | Generates a report: source-vs-loaded row counts, plus savings-type-wise and loan-type-wise balance totals |

## Data quality issues handled

The sample source data deliberately contains realistic problems:

- Duplicate member records (exact duplicate, and same ID with different name casing)
- Inconsistent date formats (`2021-03-15`, `2019/11/20`, `15-04-2022`) and invalid dates (`not available`)
- Leading/trailing spaces and inconsistent casing in names and account types
- Orphan savings/loan accounts referencing members that do not exist
- Negative balances that violate business rules

## Project structure

```
cooperative-data-etl/
├── generate_sample_data.py   # creates the messy source files
├── etl_pipeline.py           # the ETL pipeline (extract→clean→validate→load→reconcile)
├── requirements.txt
├── data/
│   ├── source/               # input: members.csv, savings.xlsx, loans.csv
│   └── target/               # output: cooperative.db (SQLite)
└── reports/
    └── reconciliation_report.txt
```

## How to run

```bash
# 1. install dependencies
pip install -r requirements.txt

# 2. create the sample source data (run once)
python generate_sample_data.py

# 3. run the pipeline
python etl_pipeline.py
```

The reconciliation report is printed to the screen and saved to
`reports/reconciliation_report.txt`.

## Sample output

```
1) ROW COUNTS (source -> loaded, with rejections)
Members : source  13 -> loaded  11  (removed 2 duplicate)
Savings : source  10 -> loaded   8  (removed 1 orphan, 1 negative)
Loans   : source   7 -> loaded   5  (removed 1 orphan, 1 negative)

2) SAVINGS BALANCE BY TYPE
Fixed        :   3 account(s)  total balance =      165,000
Recurring    :   2 account(s)  total balance =       17,500
Regular      :   3 account(s)  total balance =       49,000
TOTAL        :   8 account(s)  total balance =      231,500
```

## Tech used

Python, pandas, SQLite (via Python's built-in `sqlite3`), openpyxl (for Excel).
