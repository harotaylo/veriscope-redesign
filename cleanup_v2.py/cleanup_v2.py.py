from supabase import create_client
s = create_client('https://sqaibfaniwbixviptilx.supabase.co', 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ')
print('\nStarting cleanup...\n')
offset = 0
total = 0
updated = 0
USAO = {'usao-sc': 'South Carolina', 'usao-sdms': 'Mississippi', 'usao-al': 'Alabama', 'usao-ak': 'Alaska', 'usao-ca': 'California', 'usao-tx': 'Texas', 'usao-ny': 'New York', 'usao-fl': 'Florida'}
while True:
    cases = s.table('cases').select('*').range(offset, offset + 99).execute()
    if not cases.data: break
    for case in cases.data:
        total += 1
        for code, state in USAO.items():
            if code in case.get('source_url', '').lower():
                if case.get('location') != state:
                    s.table('cases').update({'location': state}).eq('id', case['id']).execute()
                    updated += 1
                break
        if total % 200 == 0: print(f'Processed {total} | Updated {updated}')
    offset += 100
print(f'\nComplete: {total} processed, {updated} updated\n')
