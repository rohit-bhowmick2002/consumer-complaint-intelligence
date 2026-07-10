"""
Consumer Complaint Intelligence - Production ETL
Real Source: https://files.consumerfinance.gov/ccdb/complaints.csv.zip
Fallback: local raw sample generated to mimic CFPB schema

Steps:
1. Source ingestion
2. Data quality tagging
3. Deduplication logic (SCD2 style)
4. Star schema build
5. Reconciliation
"""

import pandas as pd
import numpy as np
from pathlib import Path
import hashlib
from datetime import datetime

RAW_PATH = Path(__file__).parent.parent / "data/raw/complaints_raw.csv"
PROCESSED = Path(__file__).parent.parent / "data/processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RAW_PATH, dtype=str)
df["_source_row_id"] = np.arange(len(df))

print(f"[ETL] Source rows: {len(df)}")

# --- 1. Basic parsing ---
for col in ["date_received","date_sent_to_company"]:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# --- 2. Data Quality Flags ---
df["dq_flag_missing_zip"] = df["zip_code"].isna() | (df["zip_code"].astype(str).str.strip()=="")
df["dq_flag_invalid_dates"] = df["date_received"].isna() | df["date_sent_to_company"].isna() | (df["date_sent_to_company"] < df["date_received"]) | (df["date_sent_to_company"] > pd.Timestamp("2026-02-01"))
df["dq_flag_invalid_state"] = ~df["state"].isin(["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY"])
df["dq_flag_unexpected_product"] = ~df["product"].isin([
    "Credit reporting, credit repair services, or other personal consumer reports",
    "Mortgage","Debt collection","Credit card","Checking or savings account",
    "Student loan","Money transfer, virtual currency, or money service",
    "Payday loan, title loan, or personal loan"
])
df["dq_flag_unmapped_company"] = df["company"].str.contains("UNKNOWN ENTITY")
df["dq_flag_duplicate"] = df.duplicated(subset=["complaint_id"], keep=False)
df["dq_flag_timely_breach"] = df["timely_response"]=="No"
df["dq_flag_late_arriving"] = (df["date_sent_to_company"] - df["date_received"]).dt.days > 15

df["days_to_company"] = (df["date_sent_to_company"] - df["date_received"]).dt.days

# --- 3. Reconciliation ---
source_rows = len(df)
rejected_rows = df["dq_flag_invalid_dates"].sum()  # hard reject
# keep but flag - not reject for reporting except invalid dates

rejected_df = df[df["dq_flag_invalid_dates"]]
clean_df = df[~df["dq_flag_invalid_dates"]].copy()

print(f"[ETL] Rejected rows (invalid dates): {rejected_rows}")

# duplicate treatment: keep first
clean_df = clean_df.sort_values(["complaint_id","date_received"])
before_dedup = len(clean_df)
clean_df = clean_df.drop_duplicates(subset=["complaint_id"], keep="first")
duplicate_removed = before_dedup - len(clean_df)
print(f"[ETL] Duplicate treatment removed: {duplicate_removed}")

# transformation added columns
clean_df["reporting_year"] = clean_df["date_received"].dt.year
clean_df["reporting_month"] = clean_df["date_received"].dt.month

# --- 4. Star Schema ---

# DimDate
date_range = pd.date_range(clean_df["date_received"].min(), clean_df["date_sent_to_company"].max(), freq="D")
dim_date = pd.DataFrame({"full_date": date_range})
dim_date["date_key"] = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
dim_date["year"] = dim_date["full_date"].dt.year
dim_date["quarter"] = dim_date["full_date"].dt.quarter
dim_date["month"] = dim_date["full_date"].dt.month
dim_date["month_name"] = dim_date["full_date"].dt.strftime("%B")
dim_date["day"] = dim_date["full_date"].dt.day
dim_date["day_of_week"] = dim_date["full_date"].dt.dayofweek
dim_date["is_weekend"] = dim_date["day_of_week"]>=5

# DimCompany with SCD2 simulation
companies = clean_df[["company"]].drop_duplicates()
companies["company_key"] = range(1, len(companies)+1)
companies["company_clean"] = companies["company"].str.upper().str.strip()
companies["effective_from"] = pd.Timestamp("2022-01-01")
companies["effective_to"] = pd.Timestamp("9999-12-31")
companies["is_current"] = True
companies["company_risk_tier"] = np.where(companies["company"].str.contains("EQUIFAX|Experian|TRANSUNION"), "Critical",
                                    np.where(companies["company"].str.contains("BANK OF AMERICA|CHASE|WELLS"), "High", "Medium"))
# simulate SCD2 change for one company - Type 2
mask = companies["company"]=="BANK OF AMERICA, NATIONAL ASSOCIATION"
if mask.any():
    # expire original
    companies.loc[mask, "effective_to"] = pd.Timestamp("2023-06-30")
    companies.loc[mask, "is_current"] = False
    # create new version
    new_version = companies[mask].copy()
    new_version["company_key"] = companies["company_key"].max()+1
    new_version["effective_from"] = pd.Timestamp("2023-07-01")
    new_version["effective_to"] = pd.Timestamp("9999-12-31")
    new_version["is_current"] = True
    new_version["company_clean"] = new_version["company_clean"] + " (NEW ENTITY - 2023 MERGER)"
    companies = pd.concat([companies, new_version], ignore_index=True)

dim_company = companies

# DimProduct
dim_product = clean_df[["product","sub_product"]].drop_duplicates()
dim_product["product_key"] = range(1, len(dim_product)+1)
dim_product["product_category"] = dim_product["product"].apply(lambda x: "Credit Services" if "Credit" in x else ("Lending" if "loan" in x.lower() or "Mortgage" in x else "Banking"))
dim_product["is_unexpected"] = dim_product["product"].isin(["Crypto wallet","BNPL Buy Now Pay Later","Neobank App"])

# DimGeography
dim_geo = clean_df[["state","zip_code"]].drop_duplicates()
dim_geo["geography_key"] = range(1, len(dim_geo)+1)
dim_geo["is_valid_state"] = ~dim_geo["state"].isin(["XX","ZZ","12",""])
state_region = {
    "CA":"West","TX":"South","FL":"South","NY":"Northeast","PA":"Northeast","IL":"Midwest","OH":"Midwest","GA":"South",
    "NC":"South","MI":"Midwest","NJ":"Northeast","VA":"South","WA":"West","AZ":"West","MA":"Northeast","TN":"South",
    "IN":"Midwest","MO":"Midwest","MD":"South","WI":"Midwest","CO":"West","MN":"Midwest","SC":"South","AL":"South",
    "LA":"South","KY":"South","OR":"West","OK":"South","CT":"Northeast","UT":"West","IA":"Midwest","NV":"West","AR":"South",
    "MS":"South","KS":"Midwest","NM":"West","NE":"Midwest","WV":"South","ID":"West","HI":"West","NH":"Northeast","ME":"Northeast",
    "RI":"Northeast","MT":"West","DE":"South","SD":"Midwest","ND":"Midwest","AK":"West","VT":"Northeast","WY":"West","DC":"South"
}
dim_geo["region"] = dim_geo["state"].map(state_region).fillna("Unknown")

# DimRisk
dim_risk = pd.DataFrame({
    "risk_key": [1,2,3,4],
    "risk_category": ["Data Integrity","Timeliness Breach","Unmapped Entity","High Complaint Concentration"],
    "risk_score": [15,30,40,70],
    "control_id": ["CTRL-DQ-001","CTRL-TIME-002","CTRL-MAP-003","CTRL-CONC-004"],
    "control_owner": ["Data Quality Team","Compliance Ops","Master Data Mgmt","Risk & Controls"]
})

# DimIssue
dim_issue = clean_df[["issue","sub_issue"]].drop_duplicates()
dim_issue["issue_key"] = range(1, len(dim_issue)+1)

# FactComplaints - use current companies only to avoid SCD2 duplication in fact count
dim_company_current = dim_company[dim_company["is_current"]==True] if "is_current" in dim_company.columns else dim_company
fact = clean_df.merge(dim_company_current[["company","company_key"]], on="company", how="left")\
               .merge(dim_product[["product","sub_product","product_key"]], on=["product","sub_product"], how="left")\
               .merge(dim_geo[["state","zip_code","geography_key"]], on=["state","zip_code"], how="left")\
               .merge(dim_issue[["issue","sub_issue","issue_key"]], on=["issue","sub_issue"], how="left")

# assign risk
def assign_risk(row):
    if row["dq_flag_unmapped_company"]:
        return 3
    elif row["dq_flag_timely_breach"]:
        return 2
    elif row["dq_flag_missing_zip"] or row["dq_flag_invalid_state"]:
        return 1
    else:
        return 4 # default will be overwritten by concentration calc later; for now 1

fact["risk_key"] = fact.apply(assign_risk, axis=1)
fact["date_key_received"] = fact["date_received"].dt.strftime("%Y%m%d").astype(int)
fact["date_key_sent"] = fact["date_sent_to_company"].dt.strftime("%Y%m%d").astype(int)

fact["days_to_company"] = fact["days_to_company"].astype(int)
fact["timely_flag"] = (fact["timely_response"]=="Yes").astype(int)
fact["has_narrative_flag"] = fact["has_narrative"].astype(int)
fact["is_exception"] = (fact["timely_flag"]==0) | fact["dq_flag_unmapped_company"] | fact["dq_flag_unexpected_product"]
fact["complaint_hash"] = fact["complaint_id"].astype(str).apply(lambda x: hashlib.md5(x.encode()).hexdigest()[:8])

# Keep necessary columns
fact_cols = ["complaint_id","date_key_received","date_key_sent","company_key","product_key","geography_key","issue_key","risk_key",
             "days_to_company","timely_flag","has_narrative_flag","is_exception","dq_flag_missing_zip","dq_flag_unexpected_product","dq_flag_unmapped_company","dq_flag_late_arriving","complaint_hash"]
fact_final = fact[fact_cols]

# --- 5. Reconciliation output ---
reporting_rows = len(fact_final)
recon = {
    "source_rows": int(source_rows),
    "rejected_invalid_dates": int(rejected_rows),
    "duplicate_removed": int(duplicate_removed),
    "transformations_added": ["date_key enrichment","risk scoring","hash keys"],
    "reporting_rows": int(reporting_rows),
    "equation_check": f"{source_rows} - {rejected_rows} - {duplicate_removed} - {(source_rows - rejected_rows - duplicate_removed - reporting_rows)} transformed = {reporting_rows}",
    "reconciliation_pass": bool((source_rows - rejected_rows - duplicate_removed) == reporting_rows)
}

import json
with open(PROCESSED / "reconciliation.json","w") as f:
    json.dump(recon,f,indent=2)

# save
dim_date.to_csv(PROCESSED / "DimDate.csv", index=False)
dim_company.to_csv(PROCESSED / "DimCompany.csv", index=False)
dim_product.to_csv(PROCESSED / "DimProduct.csv", index=False)
dim_geo.to_csv(PROCESSED / "DimGeography.csv", index=False)
dim_risk.to_csv(PROCESSED / "DimRisk.csv", index=False)
dim_issue.to_csv(PROCESSED / "DimIssue.csv", index=False)
fact_final.to_csv(PROCESSED / "FactComplaints.csv", index=False)
clean_df.to_csv(PROCESSED / "complaints_clean.csv", index=False)
rejected_df.to_csv(PROCESSED / "complaints_rejected.csv", index=False)
df.to_csv(PROCESSED / "complaints_quality_flagged.csv", index=False)

print(f"[ETL] Saved star schema to {PROCESSED}")
print(recon)
