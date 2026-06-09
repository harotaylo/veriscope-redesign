#!/usr/bin/env python3
import json
import requests
import hashlib
import re
from datetime import datetime

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

CIRCUITS = {
    '1': {'name': '1st Circuit', 'states': ['ME', 'MA', 'NH', 'RI', 'PR']},
    '2': {'name': '2nd Circuit', 'states': ['CT', 'NY', 'VT']},
    '3': {'name': '3rd Circuit', 'states': ['DE', 'NJ', 'PA', 'VI']},
    '4': {'name': '4th Circuit', 'states': ['MD', 'NC', 'SC', 'VA', 'WV']},
    '5': {'name': '5th Circuit', 'states': ['LA', 'MS', 'TX']},
    '6': {'name': '6th Circuit', 'states': ['KY', 'MI', 'OH', 'TN']},
    '7': {'name': '7th Circuit', 'states': ['IL', 'IN', 'WI']},
    '8': {'name': '8th Circuit', 'states': ['AR', 'IA', 'MN', 'MO', 'NE', 'ND', 'SD']},
    '9': {'name': '9th Circuit', 'states': ['AK', 'AZ', 'CA', 'HI', 'ID', 'MT', 'NV', 'OR', 'WA']},
    '10': {'name': '10th Circuit', 'states': ['CO', 'KS', 'NM', 'OK', 'UT', 'WY']},
    '11': {'name': '11th Circuit', 'states': ['AL', 'FL', 'GA']},
    'DC': {'name': 'DC Circuit', 'states': ['DC']},
    'Fed': {'name': 'Federal Circuit', 'states': ['US']}
}

def get_position(text):
    positions = ['judge', 'senator', 'official', 'officer', 'defendant']
    text_lower = text.lower()
    for pos in positions:
        if pos in text_lower:
            return 'Judge' if pos == 'judge' else 'Official'
    return 'Official'

def get_location(circuit_code, states):
    if circuit_code == 'DC':
        return 'DC'
    elif circuit_code == 'Fed':
        return 'Federal'
    else:
        return states[0] if states else 'Federal'

def get_status(text):
    text_lower = text.lower()
    
    if 'convicted' in text_lower or 'guilty' in text_lower:
        return 'Convicted'
    elif 'indicted' in text_lower:
        return 'Indicted'
    elif 'dismissed' in text_lower:
        return 'Dismissed'
    elif 'acquitted' in text_lower:
        return 'Acquitted'
    else:
        return 'Convicted'

def scrape_circuits():
    print("\n" + "="*70)
    print("VeriScope - Federal Circuit Courts Scraper")
    print("="*70 + "\n")
    
    all_cases = []
    base_url = "https://www.courtlistener.com/api/rest/v3/opinions/"
    
    keywords = [
        'convicted judge',
        'federal official corruption',
        'bribery federal',
        'public official guilty',
        'fraud conviction',
        'misconduct judge'
    ]
    
    for circuit_code, circuit_info in CIRCUITS.items():
        circuit_name = circuit_info['name']
        states = circuit_info['states']
        
        print(f"\n{circuit_name}")
        print("-" * 70)
        
        for keyword in keywords:
            print(f"  Searching: {keyword}")
            
            try:
                params = {
                    'q': f"{keyword} {circuit_name}",
                    'page': 1,
                    'page_size': 50,
                    'order_by': '-date_filed'
                }
                
                resp = requests.get(base_url, params=params, timeout=10)
                
                if resp.status_code != 200:
                    continue
                
                data = resp.json()
                results = data.get('results', [])
                
                if not results:
                    continue
                
                print(f"    Found: {len(results)}")
                
                for result in results:
                    try:
                        case_name = result.get('case_name', '')
                        opinion_text = result.get('plain_text', '')[:1000]
                        url = result.get('absolute_url', '')
                        
                        if not case_name or len(case_name) < 5:
                            continue
                        
                        combined = f"{case_name} {opinion_text}".lower()
                        
                        if not any(w in combined for w in ['judge', 'official', 'convicted', 'guilty', 'corruption', 'bribery']):
                            continue
                        
                        if ' v. ' in case_name:
                            name = case_name.split(' v. ')[0].strip()[:100]
                        else:
                            name = case_name.split(',')[0][:100]
                        
                        if not name or name.isupper():
                            name = 'Unknown Official'
                        
                        case = {
                            'full_name': name,
                            'title': case_name[:150],
                            'position_title': get_position(combined),
                            'official_type': 'Judicial',
                            'location': get_location(circuit_code, states),
                            'level': 'Federal',
                            'category': 'Corruption',
                            'abuse_of_power_type': 'Corruption',
                            'case_status': get_status(combined),
                            'details': opinion_text[:1000],
                            'source_url': url,
                            'source_type': 'court_record',
                            'source_date': str(datetime.now().date()),
                            'publication_status': 'draft',
                            'verified_by': 'circuit_scraper',
                            'verified_at': datetime.now().isoformat(),
                            'fingerprint': hashlib.md5(url.encode()).hexdigest()[:16]
                        }
                        
                        all_cases.append(case)
                        print(f"      [+] {case_name[:50]}")
                    
                    except:
                        continue
            
            except Exception as e:
                continue
        
        print(f"  Total so far: {len(all_cases)}")
    
    return all_cases

def upload_to_supabase(cases):
    if not cases:
        print("\nNo cases to upload")
        return 0
    
    print(f"\n" + "="*70)
    print(f"Total scraped: {len(cases)}")
    
    statuses = {}
    locations = {}
    
    for c in cases:
        statuses[c['case_status']] = statuses.get(c['case_status'], 0) + 1
        locations[c['location']] = locations.get(c['location'], 0) + 1
    
    print("\nStatus Breakdown:")
    for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count}")
    
    print("\nCircuit Distribution:")
    for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True):
        print(f"  {location}: {count}")
    
    with open('circuit_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved: circuit_cases.json")
    
    print("\n" + "="*70)
    print("Deduplicating...")
    
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        resp = supabase.table('cases').select('fingerprint').execute()
        existing_fps = {row['fingerprint'] for row in resp.data}
        print(f"  Existing: {len(existing_fps)}")
        
        new_cases = [c for c in cases if c['fingerprint'] not in existing_fps]
        print(f"  New: {len(new_cases)}")
        print(f"  Duplicates: {len(cases) - len(new_cases)}")
        
        if not new_cases:
            print("\nAll cases already in database!")
            return 0
        
        print(f"\n" + "="*70)
        print(f"Uploading {len(new_cases)} cases...\n")
        
        uploaded = 0
        for i in range(0, len(new_cases), 50):
            chunk = new_cases[i:i+50]
            try:
                supabase.table('cases').insert(chunk).execute()
                uploaded += len(chunk)
                print(f"  [+] {uploaded}/{len(new_cases)}")
            except Exception as e:
                print(f"  Error: {str(e)[:60]}")
        
        return uploaded
    
    except ImportError:
        print("Supabase not available - saved to JSON only")
        return 0

if __name__ == '__main__':
    cases = scrape_circuits()
    uploaded = upload_to_supabase(cases)
    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} new cases uploaded")
    print("="*70 + "\n")