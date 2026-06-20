#!/usr/bin/env python3
from supabase import create_client
import json

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    resp = supabase.table('jurisdictions').select('*').execute()
    print("Jurisdiction Mapping:")
    print(json.dumps(resp.data, indent=2))
except Exception as e:
    print(f'Error: {e}')
