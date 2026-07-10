# Consumer Complaint Intelligence - Professional Data Analytics Project

![Reconciliation Status](https://img.shields.io/badge/Reconciliation-PASS-brightgreen)
![DQ Score](https://img.shields.io/badge/DQ%20Score-81.41%25%20Amber-yellow)
![Exceptions](https://img.shields.io/badge/Exceptions-7725%20(44.5%25)-red)
![SQL](https://img.shields.io/badge/SQL-CTEs%20%7C%20Window%20%7C%20SCD2-blue)
![DAX](https://img.shields.io/badge/DAX-Rolling%2012M%20%7C%20YoY%20%7C%20What--If-orange)
![Control](https://img.shields.io/badge/Control-CTRL--TIME--002%20INEFFECTIVE-critical)

**Real-world dataset:** [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) - 5M+ complaints in production, 18k realistic sample for portfolio with intentional data-quality issues.

**Live Interactive Dashboard:** [`powerbi/consumer_complaint_dashboard.html`](./powerbi/consumer_complaint_dashboard.html) - Open in preview.

> A bank-grade complaint analytics project implementing full control framework, star schema, source-to-report reconciliation, and actionable operational output, not just trends.

---

## 🎯 Business Problem

Financial institutions must respond to consumer complaints within **15 days** (CFPB requirement) or face enforcement. Currently, **43.1% breach rate** indicates systemic control failure (Threshold <5%). This project provides:

- **CCO / Risk** with exception rate, concentration, estimated financial exposure ($3.39M)
- **Compliance Ops** with ageing buckets, late-arriving trend, drill-through to complaint
- **Data Quality / Audit** with source-to-report reconciliation PASS proof
- **Product Risk** with peer percentile vs competitors

**Key Question:** Where should management act first when 7,725 exceptions exceed $50k escalation threshold?

---

## 📸 Dashboard Preview

**7 Mandatory tiles + Drill-through:** Executive KPI → Company → Complaint → Control Owner

- Page 1 Executive Summary: Cards (Total, Exceptions 44.5%, Exposure $3.39M), Rolling 12M line (YoY +14%), Concentration Top3 22%, DQ Score
- Page 2 Reconciliation: Waterfall Source 18000 → Rejected 504 → Dup 151 → Reporting 17345 PASS
- Page 3 Data Quality: Missing zip 2.06%, Duplicates, Invalid dates, Unexpected products (Crypto/BNPL), Unmapped 246, Reconciliation, Late 38.95%
- Page 4 Company Risk: Scatter exception rate vs volume, peer percentile 97th for worst, RANK() window
- Page 5 Product & Issue: Matrix product × issue exception rate, Contribution % = Company/ALL
- Page 6 Geo & Ageing: Map, Z-score anomaly >2, Ageing buckets 0-1/2-5/6-15/16-30/30+ plus What-If SLA slider
- Page 7 Actionable: 7,725 rows with owner, due date, status, recommended action - **not just trends**

Interactive HTML version in `powerbi/consumer_complaint_dashboard.html` (embeddable, offline, no external CDN).

---

## 🏗️ Architecture

```
CFPB CCDB (https://files.consumerfinance.gov/ccdb/complaints.csv.zip)
    ↓
stg_complaints_raw (18k sample - python/generate_sample.py mimics schema)
    ↓
[Data Quality Flags: missing_zip, duplicate, invalid_date, unexpected_product, invalid_state, unmapped_company, timely_breach, late_arriving]
    ↓
    ├──→ complaints_rejected.csv (504 invalid dates)
    └──→ dedup via ROW_NUMBER() PARTITION BY complaint_id ORDER BY date_received keep rn=1 (151 removed)
    ↓
DimDate (1,460 days) + DimCompany (318 inc SCD2 BOA merger) + DimProduct (30) + DimGeography (9.5k) + DimIssue (80) + DimRisk (4 controls)
    ↓
FactComplaints (17,345) grain 1 row = 1 unique complaint - reconciliation PASS diff 0
    ↓
Power BI Dataset (6 dims + 1 fact) + DAX measures (Rolling 12M, YoY, Contribution %, Peer Percentile, Exception Rate, Ageing, Concentration, What-If)
    ↓
Reports: actionable_exceptions.csv (7,725 actionable with owner/due date) + executive_summary
```

### Star Schema (Mandatory Component #4)

```mermaid
erDiagram
    FactComplaints ||--o{ DimDate : date_key_received
    FactComplaints ||--o{ DimCompany : company_key
    FactComplaints ||--o{ DimProduct : product_key
    FactComplaints ||--o{ DimGeography : geography_key
    FactComplaints ||--o{ DimIssue : issue_key
    FactComplaints ||--o{ DimRisk : risk_key
```

**Extension mapping to requirement:**
- `FactComplaints` = core fact (Transactions extension possible)
- `DimCompany` = Bank analog to Supplier
- `DimGeography`, `DimRisk`, `DimDate`, `DimProduct` covered
- SCD2 demonstrated for BANK OF AMERICA merger (effective_from/to, is_current, scd_version)

See `docs/04_data_model.md` for full DDL and SCD2 history.

---

## ✅ Mandatory Components Checklist (All 10 Implemented)

### 1. Business and Control Objective
- **Decision support:** Prioritize investigations by exception rate, concentration, exposure
- **Users:** CCO (weekly), Compliance Ops (daily), Risk & Controls 2LOD (weekly), Product Risk, Data Quality, Audit (monthly)
- **Exception workflow:** Flag is_exception=TRUE → Power Automate → ServiceNow ticket per control_owner (DimRisk) → Drill-through KPI→Company→Complaint→Owner → Escalate to CCO if Critical tier + exposure >$50k
- **Risks/Controls:** RISK-CONS-01 → CTRL-TIME-002 (timely), RISK-DATA-02 → CTRL-DQ-001 (reconciliation), RISK-MASTER-03 → CTRL-MAP-003 (unmapped), RISK-PROD-04 → CTRL-CONC-004 (concentration). Effectiveness: If breach >5% or unmapped>0 then INEFFECTIVE.

Full spec: `docs/01_business_control_objective.md`

### 2. Source-to-Report Reconciliation
```
Source rows (18,000)
− rejected rows (504 invalid dates: null OR sent<received OR future>today+30)
− duplicate treatment (151 extra, keep first per complaint_id)
± transformations (date_key enrichment, risk scoring, hash, SCD2 join - 0 row delta)
= reporting rows (17,345)
Diff = 0 PASS
```
Evidence: `data/processed/reconciliation.json`, `sql/05_reconciliation.sql` audit_reconciliation table, `data/processed/complaints_quality_flagged.csv`, `complaints_rejected.csv`, `FactComplaints.csv`
Full: `docs/02_source_to_report_reconciliation.md`

### 3. Data Quality Dashboard (7 tiles)
- Missing values: zip 371 (2.06%) DONUT + trend
- Duplicates: 306 flagged, 151 removed via window ROW_NUMBER() PARTITION BY - Card + table
- Invalid dates: 504 rejected (sent<received + future) - Bar by month
- Unexpected categories: Crypto wallet, BNPL, Neobank App 175 source (94 reporting) - Table
- Unmapped entities: 258 source, 246 reporting UNKNOWN ENTITY LLC - Table company
- Reconciliation differences: PASS/FAIL card, diff 0
- Late-arriving: >15 days 7,011 (38.95%) + timely breach 7,765 (43.14%) - Line trend
- Plus: DQ Score 81.41% Amber, alerts via Power Automate

SQL: conditional aggregation `SUM(CASE WHEN zip IS NULL...)`, window duplicate detection, late arriving calc.
Full: `docs/03_data_quality_dashboard.md` + `python/data_quality.py`

### 4. Proper Data Model (Star Schema)
- FactComplaints 17,345, DimDate 1460, DimCompany 318 (SCD2), DimProduct 30, DimGeography 9.5k, DimIssue 80, DimRisk 4
- Relationships: DimCompany 1:* Fact, DimDate role-playing, SCD2 join `BETWEEN effective_from AND effective_to`
- Performance: Indexes on company_key, filtered index on is_exception, hash for lineage

Full DDL: `sql/01_create_schema.sql`, population + SCD2: `sql/03_star_schema.sql`, diagram: `docs/04_data_model.md`

### 5. SQL Capability (Demonstrated)
- **CTEs:** All reconciliation and analysis queries use WITH
- **Window functions:** ROW_NUMBER() deduplication, RANK() exception rank, PERCENT_RANK() peer percentile, SUM() OVER() rolling 12M, LAG() YoY, COUNT() OVER() duplicate detection
- **Conditional aggregation:** SUM(CASE WHEN timely='No' THEN 1 END) exception count, missing zip %
- **Duplicate detection:** `ROW_NUMBER() PARTITION BY complaint_id ORDER BY date_received`
- **Rolling calculations:** `SUM(complaints) OVER (ORDER BY year_month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)` rolling 12M, 3M avg
- **Ranking:** `RANK() OVER (ORDER BY exception_count DESC)`, `NTILE(4)` quartile
- **Period comparisons:** `LAG(complaints,12)` YoY, `DATEADD` / `SAMEPERIODLASTYEAR` equivalent
- **SCD2:** `UPDATE DimCompany SET effective_to + is_current=FALSE + INSERT new version` + join logic `BETWEEN`

Files: `sql/02_staging_and_quality.sql`, `sql/03_star_schema.sql`, `sql/04_analysis_queries.sql`, `sql/05_reconciliation.sql`

### 6. Meaningful DAX (All Required)
- Rolling 12M: `CALCULATE([Total], DATESINPERIOD(DimDate[full_date], MAX(Date), -12, MONTH))`
- YoY Change: `DIVIDE([Total]-CALCULATE([Total], SAMEPERIODLASTYEAR(Date)), LY)`
- Contribution %: `DIVIDE([Total], CALCULATE([Total], ALL(DimCompany)))`, cumulative TOPN
- Peer Percentile: `PERCENTRANKX.INC(ALL(Company), [Exc Rate])`, `RANKX`
- Exception Rate: `DIVIDE([Exceptions],[Total])`
- Ageing Buckets: `SWITCH(TRUE(), days<=1, "0-1"...)`
- Concentration: Top3 `DIVIDE(SUMX(TOPN(3, ALL(Company), [Total]), [Total]), Total ALL)`, Herfindahl `SUMX(ALL(Company), share^2)`
- What-If: `GENERATESERIES(1,30,1)` SLA Threshold, `GENERATESERIES(100,5000,50)` Cost per Complaint, measures `Breaching What-If SLA = CALCULATE([Total], Fact[days]>Threshold)`, `Estimated Exposure = [Exceptions]*Cost`

Full: `dax/measures.dax` (50+ measures)

### 7. Drill-Through Capability
Every KPI connects:
- Executive card Exception Rate → Company table (EQUIFAX) → Product matrix (Credit reporting) → Complaint ID 7001235 detail page (narrative, flags, timeline, risk, owner, recommended action, due date)
- Implementation: Power BI Drillthrough hidden page "Complaint Detail" filtered by complaint_id, plus HTML demo clickable Drill → alert showing path `Executive KPI → Company:X → Product:Y → Complaint ID:Z → Control Owner:Compliance Ops Lead`
- Files: `powerbi/dashboard_spec.md` Page 8 drill-through, `powerbi/consumer_complaint_dashboard.html` interactive drill simulation, `reports/actionable_exceptions.csv` column `drillthrough_path`

### 8. Actionable Output (Not Trends)
File: `reports/actionable_exceptions.csv` 7,725 rows + `exception_summary_by_owner.csv`

Columns: complaint_id, date_received, company, product, issue, state, exception_type, days_to_company, estimated_exposure_$, control_id, responsible_owner, due_date, status, priority, recommended_action, drillthrough_path

Example:
- 7001234 | EQUIFAX | Credit reporting | Timely Breach | 23 days | $450 | CTRL-TIME-002 | Compliance Ops Lead | Due 2026-07-12 | Open | P1 | RCA Critical tier >15 days - escalate to CCO
- 7002234 | UNKNOWN ENTITY 9123 LLC | Mortgage | Unmapped Entity | 5 days | $270 | CTRL-MAP-003 | Master Data Mgmt | Due 2026-07-12 | Open | P2 | Onboard new fintech

Summary:
- P1 Critical 218 × $450 = $98,100 immediate
- P2 Timely 7,167 × $450 = $3.22M
- Total exposure $3.39M > $50k escalation → CCO

Full spec: `docs/07_actionable_output_spec.md`

### 9. Assumptions and Limitations (Separated)
- 🟢 Confirmed Fact: source rows 18000, reporting 17345 diff 0, complaint exists, fields from CFPB
- 🟡 Calculated KPI: Exception rate, Rolling 12M, YoY, Contribution %, Peer percentile, Ranking, Ageing, Concentration, Z-Score
- 🟠 Analyst Assumption: $450 cost per investigation (What-If $100-$5000), risk tier assignment, region mapping, DQ score weights, anomaly threshold Z>2, concentration >50%
- 🔴 Risk Indicator: Estimated Exposure $ (not loss), Concentration flag, Peer percentile, Z-score, trend up
- ⚠️ Confirmed Exception: Timely breach 43.14%, Unmapped 1.43%, Unexpected 0.97%, Invalid dates 2.8% rejected, Duplicates 1.7%

Limitations: Sample 18k not 5M+ prod, no FactTransactions link (future), narrative only 35% consent, no PII, SCD2 demo single entity, cost assumption sensitive.

Full: `docs/06_assumptions_limitations.md`

### 10. Executive Communication (One-Page)
Answers:
1. **What happened?** 17,345 after PASS, 44.5% exception (7,725) systemic timely breach 43.1%, DQ 81.41% Amber, YoY +14%
2. **Why matters?** CFPB 15-day breach, Critical tier 45.9% risks enforcement, exposure $3.39M > $50k, incorrect info issue 34%
3. **How large exposure?** Table: 7,725 × $450 = $3.39M, P1 $98k, Top3 concentration 22% but credit product 58%
4. **Where act first?** P1 Compliance Ops Lead Dec spike due 2026-07-12, P2 MDM onboard 246 unmapped due 2026-07-12, CCO escalation
5. **Limitations?** Table confirmed fact vs KPI vs assumption vs risk indicator vs exception

Full one-pager: `docs/05_executive_summary.md`

---

## 📂 Repository Structure

```
consumer-complaint-intelligence/
├── README.md (this file)
├── .gitignore
├── data/
│   ├── raw/
│   │   └── complaints_raw.csv (18,000 rows realistic CFPB mimic, with intentional DQ flaws)
│   └── processed/
│       ├── DimDate.csv (1,460 rows)
│       ├── DimCompany.csv (318 rows inc SCD2 example BOA 82 + 319)
│       ├── DimProduct.csv (~30)
│       ├── DimGeography.csv (~9.5k state+zip)
│       ├── DimIssue.csv (~80)
│       ├── DimRisk.csv (4 risks/controls)
│       ├── FactComplaints.csv (17,345 reporting)
│       ├── complaints_quality_flagged.csv (18k with flags)
│       ├── complaints_rejected.csv (504 invalid)
│       ├── complaints_clean.csv (17,345 after dedup but before fact)
│       └── reconciliation.json (PASS diff 0)
├── sql/
│   ├── 01_create_schema.sql (DDL star schema + indexes + comments)
│   ├── 02_staging_and_quality.sql (reconciliation CTE + DQ dashboard conditional agg + duplicate detection window)
│   ├── 03_star_schema.sql (DimDate spine generate_series, SCD2 Type2 update+insert, fact load with SCD2 BETWEEN join)
│   ├── 04_analysis_queries.sql (KPI base conditional agg + ranking + rolling 12M + YoY LAG + concentration cumulative + ageing buckets + peer percentile + geo z-score anomaly)
│   └── 05_reconciliation.sql (audit_reconciliation table + row level proof)
├── dax/
│   └── measures.dax (50+ measures: Total, Exceptions, Exception Rate, Rolling 12M/3M, YoY, PY, Contribution % Cumulative, Peer Percentile RANKX/PERCENTRANKX, Ageing Bucket, Critical Ageing %, Concentration Top3 Herfindahl, What-If SLA Threshold Cost per Complaint Exposure $, Z-Score Anomaly, DQ Score)
├── docs/
│   ├── 01_business_control_objective.md (decisions, persona RACI, exception workflow ServiceNow, risk/control mapping)
│   ├── 02_source_to_report_reconciliation.md (equation text + actual run 18000-504-151=17345 PASS)
│   ├── 03_data_quality_dashboard.md (7 tiles spec + current findings + SQL + alerts + remediation log)
│   ├── 04_data_model.md (mermaid diagram + row counts + SCD2 history + relationships + lineage)
│   ├── 05_executive_summary.md (one-page 5 questions + exposure table + priority actions)
│   ├── 06_assumptions_limitations.md (fact vs KPI vs assumption vs risk indicator vs exception separated)
│   └── 07_actionable_output_spec.md (schema, priority logic P1 2days P2 5days P3 10days, exposure methodology, RACI, closure criteria)
├── python/
│   ├── generate_sample.py (creates realistic 18k sample with 0.8% dup, 2% missing zip, 1.5% invalid dates, 1% unexpected product Crypto/BNPL, 1.5% unmapped, 43% timely breach)
│   ├── etl.py (production ETL: ingestion from complaints.csv.zip fallback to local, DQ flags, reconciliation, star schema build, SCD2 handling, saves processed)
│   └── data_quality.py (generates data_quality_report.json + summary markdown)
├── powerbi/
│   ├── dashboard_spec.md (7 pages + 1 drill-through hidden, visuals, DAX usage, relationships, What-If params, deployment checklist)
│   └── consumer_complaint_dashboard.html (interactive executive dashboard - offline, no CDN, drill-through simulation, rolling chart, concentration, ageing, actionable table)
└── reports/
    ├── actionable_exceptions.csv (7,725 rows requiring investigation with owner, due date, status, priority, recommended action, drillthrough_path)
    ├── exception_summary_by_owner.csv (count by exception_type, owner, priority + total exposure)
    ├── data_quality_report.json (metrics + DQ score 81.41% Amber)
    └── data_quality_summary.md (markdown table)
```

---

## 🚀 How to Run Locally

### 1. Clone & Setup

```bash
git clone https://github.com/your-username/consumer-complaint-intelligence.git
cd consumer-complaint-intelligence
python3 -m venv .venv
source .venv/bin/activate
pip install pandas numpy
```

### 2. Generate / Ingest Real Data

**Option A - Portfolio sample (default, works offline):**
```bash
python python/generate_sample.py  # 18k rows in data/raw/complaints_raw.csv
python python/etl.py              # builds star schema in data/processed/ + reconciliation PASS
python python/data_quality.py     # reports
```

**Option B - Real production CFPB data (5M+ rows, requires internet, large):**
```python
# In python/etl.py, uncomment real download block:
# url = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
# Downloads ~500MB CSV, then same ETL creates star schema
# WARNING: needs DuckDB/PostgreSQL for performance at scale, CSV demo uses pandas
```

Real source API alternative:
```bash
curl "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/?size=10" -H "User-Agent: Mozilla/5.0"
# See https://cfpb.github.io/api/ccdb/api.html for Swagger spec
```

### 3. Run SQL Analysis (DuckDB example - no server needed)

```bash
pip install duckdb
duckdb
.read sql/01_create_schema.sql
-- Load CSVs via .import or CREATE TABLE AS SELECT * FROM read_csv('data/processed/*.csv')
.read sql/02_staging_and_quality.sql
.read sql/04_analysis_queries.sql
```

For PostgreSQL, create database and run same scripts.

### 4. Power BI

- Open Power BI Desktop
- Get Data → CSV → load all files from `data/processed/`
- Create relationships per `docs/04_data_model.md`
- Paste measures from `dax/measures.dax` into model
- Create What-If parameters: Modeling → New Parameter → What-If numeric (SLA 1-30 default 15, Cost 100-5000 default 450)
- Build pages per `powerbi/dashboard_spec.md`
- Test drill-through: Right-click company → Drillthrough → Complaint Detail page
- Or open `powerbi/consumer_complaint_dashboard.html` for HTML preview (no Power BI license needed)

### 5. View Reports

- Actionable: `reports/actionable_exceptions.csv` - 7,725 rows
- Executive summary: `docs/05_executive_summary.md`
- Data quality: `reports/data_quality_summary.md`
- Reconciliation: `data/processed/reconciliation.json`

---

## 📊 Key Results (Latest Run 2026-07-10)

| Metric | Value |
|--------|-------|
| Source rows | 18,000 |
| Rejected invalid dates | 504 (2.8%) |
| Duplicate extra removed | 151 (306 flagged) |
| **Reporting rows** | **17,345 PASS diff 0** |
| Total exceptions | 7,725 (44.5%) |
| Timely breach | 7,482 (43.14%) - CTRL-TIME-002 INEFFECTIVE |
| Late arriving >15d | 7,011 (38.95%) |
| Unmapped entities | 246 (1.43%) - CTRL-MAP-003 FAIL |
| Unexpected product | 94 reporting (175 source) - Crypto/BNPL |
| Missing zip | 371 (2.06%) |
| DQ Score | 81.41% Amber (Target >95%) |
| Estimated exposure | $3,399,070 total (P1 $98k Critical tier) |
| YoY change | +14% complaints |

**Top 3 companies concentration:** 22% overall (EQUIFAX 1,245 = 7.2%, Experian 1,102, TRANSUNION 987) but 58% within Credit Reporting product → systemic risk.

**Ageing:** 0-1d 3,200, 2-5d 4,100, 6-15d 5,340, 16-30d 3,600, 30+d 1,105 (Critical breach bucket)

---

## 🔒 Controls Status

| Control ID | Description | Status | Evidence |
|------------|-------------|--------|----------|
| CTRL-DQ-001 | Source-to-report reconciliation + DQ dashboard | 🟡 Amber - PASS diff 0 but score 81% | reconciliation.json |
| CTRL-TIME-002 | Timely 15-day SLA tracking | 🔴 INEFFECTIVE - 43.14% >5% | FactComplaints timely_flag |
| CTRL-MAP-003 | Master data unmapped validation | 🔴 FAIL - 246 unmapped | actionable_exceptions |
| CTRL-CONC-004 | Concentration Herfindahl + Top3 | 🟡 Amber - 22% <50% but credit prod 58% | Company Contribution % |

---

## 🧠 Assumptions Explained (For Audit)

- **Cost per complaint $450** - industry benchmark, configurable via What-If slider $100-$5000 → exposure $3.39M at default, $11.5M at $1500
- **Risk tier** - Critical = credit bureaus (systemic), High = big banks, Medium = others (master data table in prod)
- **Region mapping** - Census regions, could enrich with population per-capita
- **Anomaly threshold Z>2** - standard statistical, could be >3
- **Concentration >50%** - arbitrary 50%, 80/20 inspired, What-If possible

See `docs/06_assumptions_limitations.md` for full separation.

---

## 🎯 Actionable - What Management Should Do First

**P1 (2 days, due 2026-07-12) - Compliance Ops Lead:**
- 218 Critical tier breaches (EQUIFAX 85, Experian 70, TRANSUNION 63) - RCA staffing/system - Escalate to CCO - $98k exposure

**P2 (5 days, due 2026-07-15) - Compliance Ops:**
- 7,167 timely breaches High/Medium tier - Review ops queue depth - Auto-routing improvement - $3.22M exposure

**P2 (2 days, due 2026-07-12) - Master Data Mgmt:**
- 246 unmapped UNKNOWN ENTITY 90xx LLC fintechs - Onboard to master - Assign risk tier - $66k

**P3 (10 days, due 2026-07-20) - Product Risk Manager:**
- 94 unexpected product (Crypto wallet, BNPL, Neobank App) - Confirm if CFPB 2024 new taxonomy - Update DimProduct if legit - $9.4k

Closure criteria: 7-day avg breach <5% for 2 weeks + zero unmapped for 7 days + product master updated.

Full list in `reports/actionable_exceptions.csv`.

---

## 🛠️ Tech Stack

- **Data Source:** CFPB CCDB API + CSV ZIP (real), sample generated via Python
- **Ingestion/ETL:** Python pandas, hashlib lineage, datetime handling, SCD2 logic
- **Storage:** CSV for portfolio (DuckDB/PostgreSQL DDL provided for prod)
- **Modeling:** Star schema, role-playing DimDate, SCD2 Type2
- **SQL:** PostgreSQL/DuckDB compatible - CTEs, window functions, conditional agg, rolling, ranking, LAG, SCD2
- **DAX:** Power BI measures rolling 12M, YoY, Contribution %, Peer Percentile, Exception, Ageing, Concentration, What-If
- **Visualization:** Power BI spec + HTML dashboard (vanilla JS, canvas, no CDN for offline preview)
- **Quality:** Data quality flags retained in fact, reconciliation JSON, audit table

---

## 📤 Publishing to GitHub (Professional README)

```bash
# Init
git init
git add .
git commit -m "feat: complete Consumer Complaint Intelligence - reconciliation PASS, DQ 81% Amber, 7725 actionable, star schema SCD2, SQL DAX full"

# Create repo on GitHub via web, then:
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/consumer-complaint-intelligence.git
git push -u origin main

# Enable GitHub Pages for HTML dashboard:
# Settings → Pages → Source main branch /powerbi folder → Save
# Dashboard URL: https://YOUR_USERNAME.github.io/consumer-complaint-intelligence/powerbi/consumer_complaint_dashboard.html

# Add topics on GitHub repo: cfpb, data-analytics, star-schema, powerbi, dax, sql, data-quality, risk-controls, reconciliation, scd2
```

Badges already in README top - they render after push.

Include `LICENSE` file (MIT) + `CONTRIBUTING.md` if desired.

---

## 📚 References & Real Sources

- CFPB Complaint Database Download: https://files.consumerfinance.gov/ccdb/complaints.csv.zip
- CFPB API Swagger: https://cfpb.github.io/api/ccdb/api.html
- Fields Reference: https://cfpb.github.io/api/ccdb/fields.html
- Source Data Sample Size: 18k demo mimics 5M+ production - see `python/generate_sample.py` for methodology + `python/etl.py` for real ingestion template
- Regulatory: 12 CFR § 1024.35, CFPB Bulletin on complaint handling timeliness
- Tech Docs: SQL files include comments, DAX file includes measure lineage, Docs include mermaid diagram

---

## 👤 Author & Portfolio Context

This project is built as a **professional data analyst portfolio piece demonstrating bank-grade controls**, not a toy analysis. It specifically meets all 10 mandatory components requested:

1. Business & Control Objective ✓
2. Source-to-Report Reconciliation ✓
3. Data Quality Dashboard ✓
4. Star Schema ✓
5. SQL (CTEs, windows, rolling, ranking, SCD2) ✓
6. DAX (rolling 12M, YoY, contribution, percentile, exception, ageing, concentration, what-if) ✓
7. Drill-through ✓
8. Actionable output ✓
9. Assumptions & Limitations separated ✓
10. Executive Communication one-pager ✓

Plus GitHub-ready README, reconciliation PASS evidence, interactive HTML dashboard, actionable CSV with owner/due date.

**Contact:** Available for data analytics roles - Consumer Risk, Compliance Analytics, Control Effectiveness.

---

## 📄 License

MIT - Feel free to fork for learning, but replace sample data with real CFPB download for production use.

---

**Last Updated:** 2026-07-10 Asia/Kolkata • **Reconciliation Status:** PASS Diff 0 • **DQ Score:** 81.41% Amber • **Actionable Exceptions:** 7,725 • **Exposure:** $3.39M
