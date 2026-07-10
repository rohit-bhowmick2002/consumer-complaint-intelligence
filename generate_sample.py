import pandas as pd
import random
from datetime import datetime, timedelta
import numpy as np

random.seed(42)
np.random.seed(42)

n = 18000

products = [
    ("Credit reporting, credit repair services, or other personal consumer reports", ["Incorrect information on your report","Improper use of your report","Problem with a credit reporting company's investigation"]),
    ("Mortgage", ["Applying for a mortgage","Trouble during payment process","Struggling to pay mortgage"]),
    ("Debt collection", ["Attempts to collect debt not owed","Written notification about debt","Took or threatened to take negative action"]),
    ("Credit card", ["Incorrect information on report","Getting a credit card","Fees or interest"]),
    ("Checking or savings account", ["Managing an account","Opening an account","Problem with a debit card"]),
    ("Student loan", ["Dealing with your lender or servicer","Struggling to repay your loan"]),
    ("Money transfer, virtual currency, or money service", ["Fraud or scam","Money was not available"]),
    ("Payday loan, title loan, or personal loan", ["Charged fees or interest","Unable to get your money"]),
]

companies = [
    "EQUIFAX, INC.", "Experian Information Solutions Inc.", "TRANSUNION INTERMEDIATE HOLDINGS, INC.",
    "BANK OF AMERICA, NATIONAL ASSOCIATION", "JPMORGAN CHASE & CO.", "WELLS FARGO & COMPANY",
    "CAPITAL ONE FINANCIAL CORPORATION", "CITIBANK, N.A.", "U.S. BANCORP", "PNC Bank N.A.",
    "Synchrony Financial", "Navient Solutions, LLC.", "Ocwen Financial Corporation", "Nationstar Mortgage",
    "Amex", "Discover Financial Services", "Santander Consumer USA", "Ally Financial Inc.",
    "SELECT PORTFOLIO SERVICING, INC.", "Fifth Third Financial Corporation"
]

# add long tail companies
for i in range(80):
    companies.append(f"FINANCIAL CORP {i:03d}")

states = ["CA","TX","FL","NY","PA","IL","OH","GA","NC","MI","NJ","VA","WA","AZ","MA","TN","IN","MO","MD","WI","CO","MN","SC","AL","LA","KY","OR","OK","CT","UT","IA","NV","AR","MS","KS","NM","NE","WV","ID","HI","NH","ME","RI","MT","DE","SD","ND","AK","VT","WY","DC"]

issues_map = {
    "Credit reporting, credit repair services, or other personal consumer reports": ["Incorrect information on your report","Improper use of your report","Problem with a credit reporting company's investigation into an existing problem","Unable to get your credit report or credit score","Problem with fraud alerts"],
    "Mortgage": ["Applying for a mortgage or refinancing an existing mortgage","Closing on a mortgage","Trouble during payment process","Struggling to pay mortgage","Applying for a mortgage"],
}

sub_products = ["Conventional home mortgage","FHA mortgage","Credit card","General-purpose credit card","Checking account","Savings account","Vehicle loan","Private student loan","Federal student loan servicing"]

company_responses = ["Closed with explanation","Closed with non-monetary relief","Closed with monetary relief","In progress","Closed without relief","Untimely response"]
consumer_complaint_tags = ["Older American","Servicemember","Older American, Servicemember", None]
submitted_via = ["Web","Phone","Referral","Postal mail","Fax","Email"]
company_public_responses = ["Company has responded to the consumer and the CFPB and chooses not to provide a public response","Company believes it acted appropriately","Company disputes the facts",None]

start_date = datetime(2022,1,1)
end_date = datetime(2025,12,31)

rows = []
for i in range(n):
    complaint_id = 7000000 + i
    # 0.8% duplicate injection
    if i>0 and random.random()<0.008:
        complaint_id = random.choice(rows)[0] if rows else complaint_id

    date_received = start_date + timedelta(days=random.randint(0,(end_date-start_date).days), hours=random.randint(0,23))
    # typical 1-7 days to company, but inject invalid
    delta = random.randint(0,25)
    if random.random()<0.015:
        delta = random.randint(-10,-1)  # invalid: sent before received
    if random.random()<0.01:
        # future date
        date_sent = datetime(2026,8,15)+timedelta(days=random.randint(0,60))
    else:
        date_sent = date_received + timedelta(days=delta)

    prod, sub_prod_list = random.choice(products)
    # unexpected category 1%
    if random.random()<0.01:
        prod = random.choice(["Crypto wallet","BNPL Buy Now Pay Later","Neobank App"])
    sub_prod = random.choice(sub_prod_list) if isinstance(sub_prod_list,list) else random.choice(sub_products)

    # standard issue per product
    if prod in issues_map:
        issue = random.choice(issues_map[prod])
    else:
        issue = random.choice(["Incorrect information","Fees or interest","Managing an account","Fraud or scam","Problem with customer service"])
    sub_issue = random.choice([f"{issue} - inaccurate balance", f"{issue} - account status", "Account information incorrect", None, None])

    company = random.choice(companies)
    # unmapped entity 1.5%
    if random.random()<0.015:
        company = f"UNKNOWN ENTITY {random.randint(9000,9999)} LLC"

    timely = "Yes" if (date_sent - date_received).days <=15 and random.random()>0.07 else "No"
    zip_code = f"{random.randint(10000,99999)}" if random.random()>0.02 else None  # 2% missing

    state = random.choice(states)
    if random.random()<0.005:
        state = random.choice(["XX","ZZ","12",""]) # invalid

    consumer_consent = random.choice(["Consent provided","Consent not provided","Other"])
    # tags
    tags = random.choice(consumer_complaint_tags)
    submitted = random.choice(submitted_via)
    comp_resp = random.choice(company_responses)
    pub_resp = random.choice(company_public_responses)

    # narrative 35% have
    has_narrative = random.random()<0.35
    narrative = "I have been experiencing issues with my account..." if has_narrative else None

    rows.append([
        complaint_id,
        date_received.strftime("%Y-%m-%d"),
        date_sent.strftime("%Y-%m-%d"),
        prod, sub_prod,
        issue, sub_issue,
        narrative,
        company, pub_resp, comp_resp,
        timely,
        consumer_consent,
        submitted,
        state, zip_code,
        tags,
        1 if has_narrative else 0
    ])

cols = ["complaint_id","date_received","date_sent_to_company","product","sub_product","issue","sub_issue",
        "consumer_complaint_narrative","company","company_public_response","company_response_to_consumer",
        "timely_response","consumer_consent_provided","submitted_via","state","zip_code","tags","has_narrative"]

df = pd.DataFrame(rows, columns=cols)
df.to_csv("/home/user/consumer-complaint-intelligence/data/raw/complaints_raw.csv", index=False)
print(f"Generated {len(df)} rows")
print(df.head())
print(f"Duplicates: {df.duplicated(subset=['complaint_id']).sum()}")
print(f"Missing zip: {df['zip_code'].isna().sum()}")
