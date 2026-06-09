#!/usr/bin/env python3
import json
import requests
import hashlib
import re
from datetime import datetime
from bs4 import BeautifulSoup

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

POSITION_MAP = {
    'judge': 'Judge', 'senator': 'Senator', 'representative': 'Representative',
    'governor': 'Governor', 'mayor': 'Mayor', 'sheriff': 'Sheriff',
    'police': 'Police Officer', 'commissioner': 'Commissioner',
    'director': 'Director', 'chief': 'Chief', 'attorney': 'Attorney General',
    'officer': 'Officer', 'detective': 'Detective', 'agent': 'Agent',
    'treasurer': 'Treasurer', 'auditor': 'Auditor', 'council': 'Council Member',
    'prosecutor': 'Prosecutor', 'district attorney': 'District Attorney',
    'supervisor': 'Supervisor', 'congressional': 'Congressman', 'official': 'Official'
}

STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming'
}

def get_position(text):
    text_lower = text.lower()
    for keyword, position in POSITION_MAP.items():
        if keyword in text_lower:
            return position
    return 'Official'

def get_location(text):
    for state_code in STATES:
        if f" {state_code}" in text or f" {state_code}." in text:
            return state_code
    for state_code, state_name in STATES.items():
        if state_name in text:
            return state_code
    return 'Federal'

def get_status(text):
    text_lower = text.lower()
    if 'convicted' in text_lower or 'guilty plea' in text_lower or 'pleaded guilty' in text_lower:
        return 'Convicted'
    elif 'indicted' in text_lower or 'grand jury' in text_lower:
        return 'Indicted'
    elif 'charged' in text_lower and 'convicted' not in text_lower:
        return 'Indicted'
    elif 'dismissed' in text_lower:
        return 'Dismissed'
    elif 'acquitted' in text_lower or 'not guilty' in text_lower:
        return 'Acquitted'
    else:
        return 'Convicted'

def get_name(title):
    title = re.sub(r'^(Former|Retired|Ex-|U\.S\.|Federal|State)\s+', '', title, flags=re.IGNORECASE)
    if ' - ' in title:
        name = title.split(' - ')[0].strip()
        if 3 < len(name) < 150:
            return name[:100]
    for position in ['Judge', 'Mayor', 'Sheriff', 'Senator', 'Representative', 'Governor', 'Officer', 'Attorney']:
        pattern = f"{position}\\s+([A-Z][a-z]+\\s+[A-Z][a-z]+)"
        match = re.search(pattern, title)
        if match:
            return match.group(1)[:100]
    for verb in ['Convicted', 'Charged', 'Indicted', 'Sentenced', 'Pleads']:
        if verb in title:
            return title.split(verb)[0].strip()[:100]
    return 'Unknown Official'

def create_case(title, body, url, source_name, official_type, level):
    combined = f"{title} {body}"
    case = {
        'full_name': get_name(title),
        'title': title[:150],
        'position_title': get_position(combined),
        'official_type': official_type,
        'location': get_location(title),
        'level': level,
        'category': 'Corruption',
        'abuse_of_power_type': 'Corruption',
        'case_status': get_status(combined),
        'details': body[:1000],
        'source_url': url,
        'source_type': 'court_record',
        'source_date': str(datetime.now().date()),
        'publication_status': 'draft',
        'verified_by': f'metascraper_{source_name}',
        'verified_at': datetime.now().isoformat(),
        'fingerprint': hashlib.md5(url.encode()).hexdigest()[:16]
    }
    return case

def scrape_federal():
    print("\n" + "="*70)
    print("FEDERAL SOURCES - DOJ/USAO")
    print("="*70)
    
    cases = []
    url = "https://www.justice.gov/api/v1/press_releases.json"
    
    searches = [
        'judge convicted', 'federal judge indicted', 'judge guilty plea',
        'congressman convicted', 'senator guilty', 'representative convicted',
        'governor convicted', 'attorney general charged',
        'police officer convicted', 'police chief indicted', 'sheriff convicted',
        'detective guilty', 'federal agent indicted', 'FBI agent guilty',
        'bribery government official', 'corruption public official',
        'embezzlement official', 'fraud federal employee',
        'mayor convicted', 'mayor indicted', 'government official corruption'
    ]
    
    for search_term in searches:
        print(f"  {search_term:40}", end='', flush=True)
        try:
            params = {
                'parameters[title]': search_term,
                'page': 0,
                'pagesize': 100
            }
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                print(f" [Error: {resp.status_code}]")
                continue
            
            data = resp.json()
            results = data.get('results', [])
            print(f" Found: {len(results)}")
            
            for result in results:
                try:
                    title = result.get('title', '')
                    body = result.get('body', '')
                    source_url = result.get('url', '')
                    if title and len(title) > 5:
                        case = create_case(title, body, source_url, 'federal', 'Executive', 'Federal')
                        cases.append(case)
                except:
                    continue
        except Exception as e:
            print(f" [Exception: {str(e)[:30]}]")
            continue
    
    print(f"\nFederal total: {len(cases)}")
    return cases

def scrape_state_ag():
    print("\n" + "="*70)
    print("STATE SOURCES - Attorney General Offices")
    print("="*70)
    
    cases = []
    
    searches_state = [
        'state official convicted', 'state attorney general indicted',
        'state senator guilty', 'state representative convicted',
        'governor charged', 'state judge indicted',
        'public corruption state', 'state employee embezzlement'
    ]
    
    for search_term in searches_state:
        print(f"  {search_term:40}", end='', flush=True)
        try:
            url = "https://www.justice.gov/api/v1/press_releases.json"
            params = {
                'parameters[title]': f"{search_term} state",
                'page': 0,
                'pagesize': 50
            }
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                print(f" Found: {len(results)}")
                
                for result in results:
                    try:
                        title = result.get('title', '')
                        body = result.get('body', '')
                        source_url = result.get('url', '')
                        if title and len(title) > 5 and any(state in title for state in STATES.values()):
                            case = create_case(title, body, source_url, 'state_ag', 'Executive', 'State')
                            cases.append(case)
                    except:
                        continue
            else:
                print(f" [Status: {resp.status_code}]")
        except Exception as e:
            print(f" [Exception: {str(e)[:30]}]")
            continue
    
    print(f"\nState AG total: {len(cases)}")
    return cases

def scrape_local():
    print("\n" + "="*70)
    print("LOCAL SOURCES - County/City Prosecutors")
    print("="*70)
    
    cases = []
    
    searches_local = [
        'mayor indicted city', 'city council convicted',
        'county commissioner charged', 'sheriff indicted county',
        'police chief guilty', 'district attorney corruption',
        'municipal official convicted', 'county official fraud',
        'city prosecutor charged', 'local government corruption'
    ]
    
    for search_term in searches_local:
        print(f"  {search_term:40}", end='', flush=True)
        try:
            url = "https://www.justice.gov/api/v1/press_releases.json"
            params = {
                'parameters[title]': search_term,
                'page': 0,
                'pagesize': 50
            }
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                print(f" Found: {len(results)}")
                
                for result in results:
                    try:
                        title = result.get('title', '')
                        body = result.get('body', '')
                        source_url = result.get('url', '')
                        if title and len(title) > 5:
                            case = create_case(title, body, source_url, 'local', 'Executive', 'Local')
                            cases.append(case)
                    except:
                        continue
            else:
                print(f" [Status: {resp.status_code}]")
        except Exception as e:
            print(f" [Exception: {str(e)[:30]}]")
            continue
    
    print(f"\nLocal total: {len(cases)}")
    return cases

def scrape_ethics():
    print("\n" + "="*70)
    print("STATE ETHICS & JUDICIAL DISCIPLINE")
    print("="*70)
    
    cases = []
    
    searches_ethics = [
        'judicial misconduct removed', 'ethics violation official',
        'judicial discipline suspension', 'state bar discipline',
        'judicial censure', 'disqualified judge', 'ethics board violation'
    ]
    
    for search_term in searches_ethics:
        print(f"  {search_term:40}", end='', flush=True)
        try:
            url = "https://www.justice.gov/api/v1/press_releases.json"
            params = {
                'parameters[title]': search_term,
                'page': 0,
                'pagesize': 50
            }
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                print(f" Found: {len(results)}")
                
                for result in results:
                    try:
                        title = result.get('title', '')
                        body = result.get('body', '')
                        source_url = result.get('url', '')
                        if title and len(title) > 5:
                            case = create_case(title, body, source_url, 'ethics', 'Judicial', 'State')
                            cases.append(case)
                    except:
                        continue
            else:
                print(f" [Status: {resp.status_code}]")
        except Exception as e:
            print(f" [Exception: {str(e)[:30]}]")
            continue
    
    print(f"\nEthics total: {len(cases)}")
    return cases

def upload_to_supabase(all_cases):
    if not all_cases:
        print("\nNo cases to upload")
        return 0
    
    print(f"\n" + "="*70)
    print(f"UPLOAD SUMMARY")
    print("="*70)
    print(f"Total scraped: {len(all_cases)}")
    
    statuses = {}
    positions = {}
    official_types = {}
    levels = {}
    
    for c in all_cases:
        statuses[c['case_status']] = statuses.get(c['case_status'], 0) + 1
        positions[c['position_title']] = positions.get(c['position_title'], 0) + 1
        official_types[c['official_type']] = official_types.get(c['official_type'], 0) + 1
        levels[c['level']] = levels.get(c['level'], 0) + 1
    
    print("\nBy Level:")
    for level, count in sorted(levels.items(), key=lambda x: x[1], reverse=True):
        print(f"  {level}: {count}")
    
    print("\nBy Official Type:")
    for otype, count in sorted(official_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {otype}: {count}")
    
    print("\nBy Status:")
    for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count}")
    
    print("\nTop Positions:")
    for position, count in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {position}: {count}")
    
    with open('metascraper_all_cases.json', 'w') as f:
        json.dump(all_cases, f, indent=2)
    print(f"\nSaved: metascraper_all_cases.json")
    
    print(f"\n" + "="*70)
    print("Deduplicating and uploading...")
    
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        resp = supabase.table('cases').select('fingerprint').execute()
        existing_fps = {row['fingerprint'] for row in resp.data}
        print(f"  Existing in DB: {len(existing_fps)}")
        
        new_cases = [c for c in all_cases if c['fingerprint'] not in existing_fps]
        print(f"  New cases found: {len(new_cases)}")
        print(f"  Duplicates filtered: {len(all_cases) - len(new_cases)}")
        
        if not new_cases:
            print("\nAll cases already in database!")
            return 0
        
        print(f"\nUploading {len(new_cases)} cases...\n")
        
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
    print("\n" + "="*70)
    print("VeriScope METASCRAPER - ALL LEVELS")
    print("Federal + State + County + Local + Ethics")
    print("="*70)
    
    federal = scrape_federal()
    state_ag = scrape_state_ag()
    local = scrape_local()
    ethics = scrape_ethics()
    
    all_cases = federal + state_ag + local + ethics
    
    uploaded = upload_to_supabase(all_cases)
    
    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} new cases uploaded")
    print(f"Database now has: ~{2271 + uploaded} total cases")
    print("="*70 + "\n")