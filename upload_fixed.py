import json
import os
from datetime import datetime

os.environ["SUPABASE_URL"] = "https://sqaibfaniwbixviptilx.supabase.co"
os.environ["SUPABASE_KEY"] = "sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ"

from supabase import create_client
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

with open("cases_with_names.json") as f:
    cases = json.load(f)

print(f"Preparing {len(cases)} cases...\n")

for case in cases:
    if not case.get("source_date"):
        case["source_date"] = case.get("date_charged", datetime.now().strftime("%Y-%m-%d"))
    if not case.get("first_name"):
        case["first_name"] = "Unknown"
    if not case.get("last_name"):
        case["last_name"] = "Official"
    if not case.get("full_name"):
        case["full_name"] = case.get("first_name", "Unknown") + " " + case.get("last_name", "Official")

print(f"Uploading {len(cases)} cases with source_date...\n")

success = 0
errors = 0

for i, case in enumerate(cases):
    if i % 100 == 0:
        print(f"Progress: {i}/{len(cases)}")
    
    try:
        response = supabase.table("cases").insert(case).execute()
        success += 1
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            pass
        else:
            errors += 1

print(f"\nUpload complete!")
print(f"Success: {success}")
print(f"Errors: {errors}")
print(f"Total: {len(cases)}")

input("Press Enter...")
