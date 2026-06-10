"""
generate_sample_data.py
========================
Creates realistic but MESSY source data for the ETL pipeline to clean.

This imitates what a cooperative hands over before migration: data exported
from different systems, with duplicates, inconsistent date formats, stray
spaces, mixed upper/lower case, broken references, and bad values.

It writes three source files into data/source/:
    - members.csv   (member master list)
    - savings.xlsx  (savings accounts)
    - loans.csv     (loan accounts)

Run this ONCE before running etl_pipeline.py.
"""

import os
import pandas as pd

SOURCE_DIR = os.path.join("data", "source")
os.makedirs(SOURCE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. MEMBERS  -- the master list of cooperative members.
#    Notice the deliberate problems in the comments. The pipeline must fix
#    or reject each one.
# ---------------------------------------------------------------------------
members = [
    {"member_id": "M001", "full_name": "Ram Sharma",     "join_date": "2021-03-15", "phone": "9801000001"},
    {"member_id": "M002", "full_name": "Sita Devi",      "join_date": "2020-07-01", "phone": "9801000002"},
    {"member_id": "M003", "full_name": "Hari Prasad",    "join_date": "2019/11/20", "phone": "9801000003"},  # date uses slashes
    {"member_id": "M004", "full_name": "  Gita Kumari ", "join_date": "15-04-2022", "phone": "9801000004"},  # spaces + day-first date
    {"member_id": "M005", "full_name": "Bishnu Thapa",   "join_date": "2023-01-10", "phone": "9801000005"},
    {"member_id": "M006", "full_name": "Krishna Rai",    "join_date": "2022-08-05", "phone": "9801000006"},
    {"member_id": "M007", "full_name": "Maya Gurung",    "join_date": "2021-12-25", "phone": "9801000007"},
    {"member_id": "M008", "full_name": "Deepak Shah",    "join_date": "not available", "phone": "9801000008"},  # invalid date
    {"member_id": "M009", "full_name": "Anita KC",       "join_date": "2020-02-14", "phone": "9801000009"},
    {"member_id": "M010", "full_name": "Suresh Magar",   "join_date": "2023-06-30", "phone": "9801000010"},
    {"member_id": "M011", "full_name": "Sunita Lama",    "join_date": "2024-01-05", "phone": ""},             # missing phone
    # ---- duplicates below ----
    {"member_id": "M002", "full_name": "Sita Devi",      "join_date": "2020-07-01", "phone": "9801000002"},  # exact duplicate of M002
    {"member_id": "M005", "full_name": "BISHNU THAPA",   "join_date": "2023-01-10", "phone": "9801000005"},  # same id, name in CAPS
]

# ---------------------------------------------------------------------------
# 2. SAVINGS ACCOUNTS
#    savings_type comes in messy cases. Some rows point to members that do
#    not exist (orphans). One balance is negative (invalid).
# ---------------------------------------------------------------------------
savings = [
    {"savings_id": "S001", "member_id": "M001", "savings_type": "Regular",   "balance": 15000, "opened_date": "2021-04-01"},
    {"savings_id": "S002", "member_id": "M002", "savings_type": "regular",   "balance": 22000, "opened_date": "2020-07-10"},  # lowercase type
    {"savings_id": "S003", "member_id": "M003", "savings_type": "FIXED",     "balance": 50000, "opened_date": "2019-12-01"},  # uppercase type
    {"savings_id": "S004", "member_id": "M004", "savings_type": "Recurring", "balance": 8000,  "opened_date": "2022-05-01"},
    {"savings_id": "S005", "member_id": "M005", "savings_type": "Fixed",     "balance": 75000, "opened_date": "2023-02-01"},
    {"savings_id": "S006", "member_id": "M006", "savings_type": "Regular",   "balance": 12000, "opened_date": "2022-09-01"},
    {"savings_id": "S007", "member_id": "M007", "savings_type": "Recurring", "balance": 9500,  "opened_date": "2022-01-15"},
    {"savings_id": "S008", "member_id": "M099", "savings_type": "Regular",   "balance": 3000,  "opened_date": "2023-03-01"},  # M099 does not exist
    {"savings_id": "S009", "member_id": "M009", "savings_type": "Regular",   "balance": -500,  "opened_date": "2020-03-01"},  # negative balance
    {"savings_id": "S010", "member_id": "M010", "savings_type": "Fixed",     "balance": 40000, "opened_date": "2023-07-01"},
]

# ---------------------------------------------------------------------------
# 3. LOAN ACCOUNTS
#    Same kinds of issues: messy loan_type case, an orphan reference, and a
#    negative outstanding balance.
# ---------------------------------------------------------------------------
loans = [
    {"loan_id": "L001", "member_id": "M001", "loan_type": "Agriculture", "principal": 100000, "outstanding": 60000, "disbursed_date": "2022-01-10"},
    {"loan_id": "L002", "member_id": "M002", "loan_type": "business",     "principal": 200000, "outstanding": 120000, "disbursed_date": "2021-03-05"},  # lowercase
    {"loan_id": "L003", "member_id": "M005", "loan_type": "PERSONAL",     "principal": 50000,  "outstanding": 25000, "disbursed_date": "2023-04-01"},  # uppercase
    {"loan_id": "L004", "member_id": "M006", "loan_type": "Agriculture", "principal": 150000, "outstanding": 90000, "disbursed_date": "2022-10-01"},
    {"loan_id": "L005", "member_id": "M088", "loan_type": "Business",     "principal": 80000,  "outstanding": 40000, "disbursed_date": "2023-01-01"},  # M088 does not exist
    {"loan_id": "L006", "member_id": "M009", "loan_type": "Personal",     "principal": 30000,  "outstanding": -10000, "disbursed_date": "2020-05-01"},  # negative outstanding
    {"loan_id": "L007", "member_id": "M010", "loan_type": "Agriculture", "principal": 120000, "outstanding": 70000, "disbursed_date": "2023-08-01"},
]

# ---------------------------------------------------------------------------
# Write the three source files. members + loans as CSV, savings as Excel,
# to mimic data arriving in different formats (just like real migrations).
# ---------------------------------------------------------------------------
pd.DataFrame(members).to_csv(os.path.join(SOURCE_DIR, "members.csv"), index=False)
pd.DataFrame(savings).to_excel(os.path.join(SOURCE_DIR, "savings.xlsx"), index=False)
pd.DataFrame(loans).to_csv(os.path.join(SOURCE_DIR, "loans.csv"), index=False)

print("Sample source data created in data/source/:")
print(f"  members.csv  -> {len(members)} rows (includes 2 duplicates, bad dates, spaces)")
print(f"  savings.xlsx -> {len(savings)} rows (includes 1 orphan, 1 negative balance, messy types)")
print(f"  loans.csv    -> {len(loans)} rows (includes 1 orphan, 1 negative balance, messy types)")
