import json
import os
os.environ["SUPABASE_URL"] = "https://sqaibfaniwbixviptilx.supabase.co"
os.environ["SUPABASE_KEY"] = "sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ"

from supabase import create_client
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

with open("cases_with_names.json") as f:
    cases = json.load(f)

print(f"Uploading {len(cases)} cases with proper names...\n")

success = 0
errors = 0

for i, case in enumerate(cases):
    if i % 50 == 0:
        print(f"Progress: {i}/{len(cases)}")
    
    try:
        response = supabase.table("cases").insert(case).execute()
        success += 1
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            pass
        else:
            errors += 1
            if errors <= 3:
                print(f"Error: {e}")

print(f"\nUpload complete!")
print(f"Success: {success}")
print(f"Duplicates/Errors: {errors}")
print(f"Total: {len(cases)}")

input("Press Enter...")
