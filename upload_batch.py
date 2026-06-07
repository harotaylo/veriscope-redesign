import json
import os
from datetime import datetime

os.environ["SUPABASE_URL"] = "https://sqaibfaniwbixviptilx.supabase.co"
os.environ["SUPABASE_KEY"] = "sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ"

from supabase import create_client
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

with open("cases_with_names.json") as f:
    cases = json.load(f)

print(f"Uploading {len(cases)} cases in batches...\n")

success = 0
errors = 0
batch_size = 25

for batch_num in range(0, len(cases), batch_size):
    batch = cases[batch_num:batch_num+batch_size]
    
    for case in batch:
        if not case.get("source_date"):
            case["source_date"] = case.get("date_charged", "2026-01-01")
    
    try:
        response = supabase.table("cases").insert(batch).execute()
        success += len(batch)
        print(f"Batch {batch_num//batch_size + 1}: Uploaded {len(batch)} cases")
    except Exception as e:
        print(f"Batch error: {e}")
        errors += len(batch)

print(f"\nComplete! Success: {success}, Errors: {errors}")
input("Press Enter...")
