"""
Data Quality Dashboard Generator
Outputs JSON metrics for Power BI and markdown report
"""
import pandas as pd
from pathlib import Path
import json

RAW = Path("../data/raw/complaints_raw.csv")
FLAGGED = Path("../data/processed/complaints_quality_flagged.csv")
OUT = Path("../reports/data_quality_report.json")
OUT.parent.mkdir(exist_ok=True)

df = pd.read_csv(FLAGGED)

total = len(df)
metrics = {
    "total_source": int(total),
    "missing_zip": int(df["dq_flag_missing_zip"].sum()),
    "pct_missing_zip": round(df["dq_flag_missing_zip"].mean()*100,2),
    "duplicates": int(df["dq_flag_duplicate"].sum()),
    "invalid_dates": int(df["dq_flag_invalid_dates"].sum()),
    "pct_invalid_dates": round(df["dq_flag_invalid_dates"].mean()*100,2),
    "unexpected_product": int(df["dq_flag_unexpected_product"].sum()),
    "pct_unexpected": round(df["dq_flag_unexpected_product"].mean()*100,2),
    "invalid_state": int(df["dq_flag_invalid_state"].sum()),
    "unmapped_company": int(df["dq_flag_unmapped_company"].sum()),
    "pct_unmapped": round(df["dq_flag_unmapped_company"].mean()*100,2),
    "timely_breach": int(df["dq_flag_timely_breach"].sum()),
    "pct_breach": round(df["dq_flag_timely_breach"].mean()*100,2),
    "late_arriving": int(df["dq_flag_late_arriving"].sum()),
    "pct_late": round(df["dq_flag_late_arriving"].mean()*100,2),
}

# DQ Score weighted
score = 100 - (metrics["pct_missing_zip"]*0.5 + metrics["pct_invalid_dates"]*3 + metrics["pct_unmapped"]*2.5 + metrics["pct_unexpected"]*0.5 + (metrics["duplicates"]/total*100)*3)
metrics["dq_score"] = round(max(0, score),2)
metrics["dq_status"] = "Green" if score>=95 else ("Amber" if score>=80 else "Red")

with open(OUT, "w") as f:
    json.dump(metrics, f, indent=2)

print(json.dumps(metrics, indent=2))

# Also generate markdown table for docs
md = f"""
| Check | Count | % | Status |
|-------|-------|---|--------|
| Missing zip | {metrics['missing_zip']} | {metrics['pct_missing_zip']}% | {'PASS' if metrics['pct_missing_zip']<1 else 'AMBER'} |
| Duplicates | {metrics['duplicates']} | {round(metrics['duplicates']/total*100,2)}% | AUTO-FIXED |
| Invalid dates | {metrics['invalid_dates']} | {metrics['pct_invalid_dates']}% | REJECTED |
| Unexpected product | {metrics['unexpected_product']} | {metrics['pct_unexpected']}% | REVIEW |
| Invalid state | {metrics['invalid_state']} | {round(metrics['invalid_state']/total*100,2)}% | FLAGGED |
| Unmapped company | {metrics['unmapped_company']} | {metrics['pct_unmapped']}% | BLOCK |
| Timely breach | {metrics['timely_breach']} | {metrics['pct_breach']}% | BREACH |
| Late arriving >15d | {metrics['late_arriving']} | {metrics['pct_late']}% | BREACH |
| DQ Score | - | {metrics['dq_score']}% | {metrics['dq_status']} |
"""

Path("../reports/data_quality_summary.md").write_text(md)
print(md)
