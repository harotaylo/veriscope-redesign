from supabase import create_client
from datetime import datetime

s = create_client('https://sqaibfaniwbixviptilx.supabase.co', 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ')

print('\n' + '='*70)
print('🧹 VeriScope Location Cleanup')
print('='*70 + '\n')

USAO_TO_STATE = {
    'usao-sc': 'South Carolina',
    'usao-sdms': 'Mississippi',
    'usao-sdms': 'Mississippi',
    'usao-al': 'Alabama',
    'usao-ak': 'Alaska',
    'usao-cdca': 'California',
    'usao-sdca': 'California',
    'usao-edtx': 'Texas',
    'usao-sdtx': 'Texas',
    'usao-sdny': 'New York',
    'usao-sdfl': 'Florida',
}

offset = 0
total = 0
updated = 0

print('Processing cases...\n')

while True:
    cases = s.table('cases').select('*').range(offset, offset + 99).execute()
    if not cases.data:
        break
    
    for case in cases.data:
        total += 1
        source_url = case.get('source_url', '').lower()
        current_location = case.get('location', '')
        
        for code, state_name in USAO_TO_STATE.items():
            if code in source_url:
                if current_location != state_name:
                    s.table('cases').update({'location': state_name}).eq('id', case['id']).execute()
                    updated += 1
                break
        
        if total % 100 == 0:
            print(f'✓ Processed {total} | Updated {updated}')
    
    offset += 100

print('\n' + '='*70)
print('✅ CLEANUP COMPLETE')
print('='*70)
print(f'\nTotal processed: {total}')
print(f'Location updated: {updated}\n')