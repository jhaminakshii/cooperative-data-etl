"""
etl_pipeline.py
===============
A small end-to-end ETL (Extract -> Transform -> Load) pipeline for
cooperative member, savings, and loan data.

It does exactly what a real data migration does, just in Python instead of
pure SQL:

    1. EXTRACT    read raw data from CSV and Excel source files
    2. CLEAN      trim spaces, fix casing, standardise dates
    3. VALIDATE   drop duplicates, reject orphan accounts and bad values
    4. LOAD       write the clean data into a SQLite database (the "target")
    5. RECONCILE  produce a report: row counts in vs out, and balance totals
                  broken down by savings type and loan type

Run order:
    python generate_sample_data.py     # once, to create the source files
    python etl_pipeline.py             # the pipeline itself
"""

import os
import sqlite3
import pandas as pd

SOURCE_DIR = os.path.join("data", "source")
TARGET_DB  = os.path.join("data", "target", "cooperative.db")
REPORT_PATH = os.path.join("reports", "reconciliation_report.txt")

# A place to collect numbers as we go, so the final report can use them.
stats = {}


# ===========================================================================
# STEP 1 — EXTRACT
# Read each source file into a pandas DataFrame. A DataFrame is just an
# in-memory table: rows and columns, exactly like a SQL table.
# ===========================================================================
def extract():
    print("STEP 1  EXTRACT  -- reading source files")
    members = pd.read_csv(os.path.join(SOURCE_DIR, "members.csv"), dtype=str)
    savings = pd.read_excel(os.path.join(SOURCE_DIR, "savings.xlsx"))
    loans   = pd.read_csv(os.path.join(SOURCE_DIR, "loans.csv"))

    stats["members_source_rows"] = len(members)
    stats["savings_source_rows"] = len(savings)
    stats["loans_source_rows"]   = len(loans)

    print(f"        members: {len(members)} rows | savings: {len(savings)} rows | loans: {len(loans)} rows")
    return members, savings, loans


# ---------------------------------------------------------------------------
# A small helper to standardise dates. The source has dates in several
# formats ("2021-03-15", "2019/11/20", "15-04-2022") and some junk
# ("not available"). pd.to_datetime tries to understand each one; anything
# it cannot parse becomes NaT (pandas' "missing date"), which we can detect.
#
# format="mixed" lets pandas read each value's format on its own. We do NOT
# set dayfirst=True, because that would wrongly flip ISO dates like
# "2020-07-01" into 7 January. For a clearly day-first value like "15-04-2022"
# pandas still gets it right, because 15 cannot be a month.
# ---------------------------------------------------------------------------
def parse_dates(series):
    return pd.to_datetime(series, errors="coerce", format="mixed")


# ===========================================================================
# STEP 2 + 3 — CLEAN AND VALIDATE: MEMBERS
# ===========================================================================
def clean_members(members):
    print("STEP 2  CLEAN    -- members")

    # Trim leading/trailing spaces from names ("  Gita Kumari " -> "Gita Kumari").
    members["full_name"] = members["full_name"].str.strip()

    # Standardise name casing to Title Case so "BISHNU THAPA" -> "Bishnu Thapa".
    members["full_name"] = members["full_name"].str.title()

    # Standardise the join_date into a real date column.
    members["join_date"] = parse_dates(members["join_date"])

    # --- VALIDATE ---
    print("STEP 3  VALIDATE -- members")

    # (a) Remove duplicate members. We treat member_id as the unique key,
    #     like a PRIMARY KEY in SQL. keep="first" keeps the first occurrence.
    before = len(members)
    members = members.drop_duplicates(subset=["member_id"], keep="first")
    removed_dupes = before - len(members)

    # (b) Flag rows whose join_date could not be parsed (was "not available").
    bad_dates = members["join_date"].isna().sum()

    stats["members_duplicates_removed"] = int(removed_dupes)
    stats["members_bad_dates"] = int(bad_dates)
    stats["members_loaded_rows"] = len(members)

    print(f"        removed {removed_dupes} duplicate member(s); {bad_dates} unparseable date(s) kept as empty")
    return members


# ===========================================================================
# STEP 2 + 3 — CLEAN AND VALIDATE: SAVINGS
# ===========================================================================
def clean_savings(savings, valid_member_ids):
    print("STEP 2  CLEAN    -- savings")

    # Standardise the savings_type text: strip spaces and Title-case it, so
    # "regular", "REGULAR", "Regular" all become "Regular".
    savings["savings_type"] = savings["savings_type"].astype(str).str.title().str.strip()

    # Make sure balance is a number, and dates are real dates.
    savings["balance"] = pd.to_numeric(savings["balance"], errors="coerce")
    savings["opened_date"] = parse_dates(savings["opened_date"])

    print("STEP 3  VALIDATE -- savings")
    before = len(savings)

    # (a) Referential integrity: keep only accounts whose member_id actually
    #     exists in the cleaned members table. This is the Python version of
    #     an INNER JOIN / foreign-key check. ".isin(...)" asks "is this value
    #     in the list of valid member ids?"
    savings = savings[savings["member_id"].isin(valid_member_ids)]
    orphans_removed = before - len(savings)

    # (b) Business rule: a savings balance cannot be negative.
    before2 = len(savings)
    savings = savings[savings["balance"] >= 0]
    negatives_removed = before2 - len(savings)

    stats["savings_orphans_removed"] = int(orphans_removed)
    stats["savings_negatives_removed"] = int(negatives_removed)
    stats["savings_loaded_rows"] = len(savings)

    print(f"        removed {orphans_removed} orphan account(s); {negatives_removed} negative balance(s)")
    return savings


# ===========================================================================
# STEP 2 + 3 — CLEAN AND VALIDATE: LOANS
# ===========================================================================
def clean_loans(loans, valid_member_ids):
    print("STEP 2  CLEAN    -- loans")

    loans["loan_type"] = loans["loan_type"].astype(str).str.strip().str.title()
    loans["principal"] = pd.to_numeric(loans["principal"], errors="coerce")
    loans["outstanding"] = pd.to_numeric(loans["outstanding"], errors="coerce")
    loans["disbursed_date"] = parse_dates(loans["disbursed_date"])

    print("STEP 3  VALIDATE -- loans")
    before = len(loans)
    loans = loans[loans["member_id"].isin(valid_member_ids)]      # drop orphans
    orphans_removed = before - len(loans)

    before2 = len(loans)
    loans = loans[loans["outstanding"] >= 0]                       # outstanding cannot be negative
    negatives_removed = before2 - len(loans)

    stats["loans_orphans_removed"] = int(orphans_removed)
    stats["loans_negatives_removed"] = int(negatives_removed)
    stats["loans_loaded_rows"] = len(loans)

    print(f"        removed {orphans_removed} orphan loan(s); {negatives_removed} negative outstanding")
    return loans


# ===========================================================================
# STEP 4 — LOAD
# Write each clean DataFrame into a SQLite database table. SQLite is a tiny
# file-based SQL database built into Python -- no install needed. This is the
# "target system" in migration terms. to_sql() creates/replaces the table.
# ===========================================================================
def load(members, savings, loans):
    print("STEP 4  LOAD     -- writing clean data to SQLite")
    os.makedirs(os.path.dirname(TARGET_DB), exist_ok=True)
    conn = sqlite3.connect(TARGET_DB)
    members.to_sql("members", conn, if_exists="replace", index=False)
    savings.to_sql("savings", conn, if_exists="replace", index=False)
    loans.to_sql("loans",   conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    print(f"        loaded into {TARGET_DB} (tables: members, savings, loans)")


# ===========================================================================
# STEP 5 — RECONCILE
# Build a human-readable report proving the migration is correct:
#   - how many rows came in, how many loaded, how many were rejected and why
#   - total savings balance per savings_type
#   - total loan outstanding per loan_type
# groupby(...).sum() is the Python version of SQL's GROUP BY ... SUM().
# ===========================================================================
def reconcile(members, savings, loans):
    print("STEP 5  RECONCILE-- building report")

    savings_by_type = savings.groupby("savings_type")["balance"].agg(["count", "sum"])
    loans_by_type   = loans.groupby("loan_type")["outstanding"].agg(["count", "sum"])

    lines = []
    lines.append("=" * 60)
    lines.append("COOPERATIVE DATA MIGRATION - RECONCILIATION REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append("1) ROW COUNTS (source -> loaded, with rejections)")
    lines.append("-" * 60)
    lines.append(f"Members : source {stats['members_source_rows']:>3} -> loaded {stats['members_loaded_rows']:>3}"
                 f"  (removed {stats['members_duplicates_removed']} duplicate)")
    lines.append(f"Savings : source {stats['savings_source_rows']:>3} -> loaded {stats['savings_loaded_rows']:>3}"
                 f"  (removed {stats['savings_orphans_removed']} orphan, {stats['savings_negatives_removed']} negative)")
    lines.append(f"Loans   : source {stats['loans_source_rows']:>3} -> loaded {stats['loans_loaded_rows']:>3}"
                 f"  (removed {stats['loans_orphans_removed']} orphan, {stats['loans_negatives_removed']} negative)")
    lines.append("")
    lines.append("2) SAVINGS BALANCE BY TYPE")
    lines.append("-" * 60)
    for stype, row in savings_by_type.iterrows():
        lines.append(f"{stype:<12} : {int(row['count']):>3} account(s)  total balance = {row['sum']:>12,.0f}")
    lines.append(f"{'TOTAL':<12} : {int(savings_by_type['count'].sum()):>3} account(s)  "
                 f"total balance = {savings_by_type['sum'].sum():>12,.0f}")
    lines.append("")
    lines.append("3) LOAN OUTSTANDING BY TYPE")
    lines.append("-" * 60)
    for ltype, row in loans_by_type.iterrows():
        lines.append(f"{ltype:<12} : {int(row['count']):>3} loan(s)     total outstanding = {row['sum']:>12,.0f}")
    lines.append(f"{'TOTAL':<12} : {int(loans_by_type['count'].sum()):>3} loan(s)     "
                 f"total outstanding = {loans_by_type['sum'].sum():>12,.0f}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("Report generated successfully. Migration ready for sign-off.")
    lines.append("=" * 60)

    report = "\n".join(lines)
    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    print(f"        report written to {REPORT_PATH}\n")
    print(report)


# ===========================================================================
# MAIN — run the five stages in order.
# ===========================================================================
def main():
    members, savings, loans = extract()

    members = clean_members(members)

    # The list of valid member ids comes from the CLEANED members table.
    # Savings/loans are only kept if they reference one of these ids.
    valid_member_ids = set(members["member_id"])

    savings = clean_savings(savings, valid_member_ids)
    loans   = clean_loans(loans, valid_member_ids)

    load(members, savings, loans)
    reconcile(members, savings, loans)


if __name__ == "__main__":
    main()
