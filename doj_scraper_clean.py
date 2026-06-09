#!/usr/bin/env python3
import json
import requests
import hashlib
import re
from datetime import datetime

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

VALID_STATUS = ['Indicted', 'Convicted', 'Acquitted', 'Dismissed']

POSITIONS = {
    'judge': 'Judge', 'senator': 'Senator', 'representative': 'Representative',
    'governor': 'Governor', 'mayor': 'Mayor', 'sheriff': 'Sheriff',
    'police': 'Police Officer', 'commissioner': 'Commissioner',
    'director': 'Director', 'chief': 'Chief', 'attorney': 'Attorney', 'official': 'Official'
}

STATES = {
    'CA': 'California', 'TX': 'Texas', 'FL': 'Florida', 'NY': 'New York',
    'PA': 'Pennsylvania', 'IL': 'Illinois', 'OH': 'Ohio', 'GA': 'Georgia',
    'NC': 'North Carolina', 'MI': 'Michigan', 'NJ': 'New Jersey',
    'VA': 'Virginia', 'WA': 'Washington', 'AZ': 'Arizona', 'MA': 'Massachusetts'
}

def get_position(text):
    text_lower = text.lower()
    for keyword, position in POSITIONS.items():
        if keyword in text_lower:
            return position
    return 'Official'

def get_location(text):
    for state_code, state_name in STATES.items():
        if state_code in text or state_name in text:
            return state_code
    return 'Federal'

def get_status(text):
    text_lower = text.lower()
    
    if 'indicted' in text_lower or 'grand jury' in text_lower:
        return 'Indicted'
    elif 'charged' in text_lower and 'convicted' not in text_lower:
        return 'Indicted'
    elif 'acquitted' in text_lower or 'not guilty' in text_lower:
        return 'Acquitted'
    elif 'dismissed' in text_lower:
        return 'Dismissed'
    elif 'convicted' in text_lower or 'guilty' in text_lower or 'sentenced' in text_lower:
        return 'Convicted'
    else:
        return 'Convicted'

def get_name(title):
    title = re.sub(r'^(Former|Retired|Ex-)\s+', '', title, flags=re.IGNORECASE)
    
    if ' - ' in title:
        name = title.split(' - ')[0].strip()
        if 5 < len(name) < 150:
            return name[:100]
    
    match = re.search(r'(Judge|Mayor|Sheriff|Senator|Official)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', title)
    if match:
        return match.group(2)[:100]
    
    for keyword in ['Convicted', 'Charged', 'Indicted', 'Sentenced']:
        if keyword in title:
            return title.split(keyword)[0].strip()[:100]
    
    return 'Unknown Official'

def scrape_doj():
    print("\n" + "="*70)
    print("VeriScope - DOJ Scraper")
    print("="*70 + "\n")
    
    all_cases = []
    url = "https://www.justice.gov/api/v1/press_releases.json"
    
    searches = [
        'convicted judge', 'indicted official', 'federal official convicted',
        'bribery', 'corruption', 'sentenced judge', 'guilty plea official',
        'fraud conviction', 'embezzlement', 'misconduct official'
    ]
    
    for search_term in searches:
        print(f"Searching: {search_term}")
        
        try:
            params = {
                'parameters[title]': search_term,
                'page': 0,
                'pagesize': 100
            }
            
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code != 200:
                print(f"  Status: {resp.status_code}")
                continue
            
            data = resp.json()
            results = data.get('results', [])
            print(f"  Found: {len(results)}")
            
            for result in results:
                try:
                    title = result.get('title', '')
                    body = result.get('body', '')
                    source_url = result.get('url', '')
                    
                    if not title or len(title) < 5:
                        continue
                    
                    combined = f"{title} {body}"
                    
                    full_name = get_name(title)
                    position = get_position(combined)
                    location = get_location(title)
                    status = get_status(combined)
                    
                    case = {
                        'full_name': full_name,
                        'title': title[:150],
                        'position_title': position,
                        'official_type': 'Executive',
                        'location': location,
                        'level': 'Federal',
                        'category': 'Corruption',
                        'abuse_of_power_type': 'Corruption',
                        'case_status': status,
                        'details': body[:1000],
                        'source_url': source_url,
                        'source_type': 'court_record',
                        'source_date': str(datetime.now().date()),
                        'publication_status': 'draft',
                        'verified_by': 'doj_scraper',
                        'verified_at': datetime.now().isoformat(),
                        'fingerprint': hashlib.md5(source_url.encode()).hexdigest()[:16]
                    }
                    
                    all_cases.append(case)
                
                except:
                    continue
        
        except Exception as e:
            print(f"  Error: {str(e)[:60]}")
            continue
    
    return all_cases

def upload_to_supabase(cases):
    if not cases:
        print("\nNo cases to upload")
        return 0
    
    print(f"\n" + "="*70)
    print(f"Total scraped: {len(cases)}")
    
    statuses = {}
    positions = {}
    locations = {}
    
    for c in cases:
        statuses[c['case_status']] = statuses.get(c['case_status'], 0) + 1
        positions[c['position_title']] = positions.get(c['position_title'], 0) + 1
        locations[c['location']] = locations.get(c['location'], 0) + 1
    
    print("\nStatus Breakdown:")
    for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count}")
    
    print("\nTop Positions:")
    for position, count in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {position}: {count}")
    
    print("\nLocations:")
    for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {location}: {count}")
    
    with open('doj_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved: doj_cases.json")
    
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
    cases = scrape_doj()
    uploaded = upload_to_supabase(cases)
    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} new cases uploaded")
    print("="*70 + "\n")