#!/usr/bin/env python3
from supabase import create_client

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    resp = supabase.table('cases').select('id, official_type').limit(10).execute()
    print('Sample official_type values from existing cases:')
    seen = set()
    for row in resp.data:
        val = row.get('official_type')
        if val not in seen:
            print(f"  '{val}'")
            seen.add(val)
except Exception as e:
    print(f'Error: {e}')
