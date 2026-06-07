import json
import os
from datetime import datetime

os.environ["SUPABASE_URL"] = "https://sqaibfaniwbixviptilx.supabase.co"
os.environ["SUPABASE_KEY"] = "sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ"

from supabase import create_client
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

print("Deleting old cases...\n")

try:
    response = supabase.table("cases").delete().neq("id", 0).execute()
    print("Old cases deleted!\n")
except Exception as e:
    print(f"Error deleting: {e}\n")

with open("cases_with_names.json") as f:
    cases = json.load(f)

print(f"Preparing {len(cases)} cases for upload...\n")

for case in cases:
    if not case.get("source_date"):
        case["source_date"] = case.get("date_charged", "2026-01-01")
    case.pop("full_name", None)

print(f"Uploading {len(cases)} cases (first_name + last_name only)...\n")

success = 0
batch_size = 25

for batch_num in range(0, len(cases), batch_size):
    batch = cases[batch_num:batch_num+batch_size]
    
    try:
        response = supabase.table("cases").insert(batch).execute()
        success += len(batch)
        print(f"Batch {batch_num//batch_size + 1}: Uploaded {len(batch)} cases")
    except Exception as e:
        print(f"Batch error: {e}")

print(f"\nComplete! Uploaded {success} cases")
print(f"App should now show 1,337 cases with proper first_name and last_name")
print(f"\nRefresh your app at: https://veriscope-app.vercel.app")

input("Press Enter...")
