#!/usr/bin/env python3
import json
import requests
import hashlib
import re
from datetime import datetime
from bs4 import BeautifulSoup
import time

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

# STRICT OFFICIAL KEYWORDS - By Level
FEDERAL_OFFICIALS = [
    'president', 'vice president', 'cabinet secretary', 'congressman', 'congresswoman',
    'federal judge', 'federal prosecutor', 'u.s. attorney', 'assistant u.s. attorney',
    'federal agent', 'fbi agent', 'dea agent', 'senator', 'representative'
]

STATE_OFFICIALS = [
    'lieutenant governor', 'state senator', 'state representative', 'state judge',
    'state attorney general', 'state treasurer', 'state auditor', 'state inspector general',
    'state trooper', 'state police officer', 'state corrections officer', 'governor'
]

COUNTY_OFFICIALS = [
    'county commissioner', 'county judge', 'county clerk', 'district attorney',
    'county attorney', 'assistant district attorney', 'county auditor', 'county treasurer',
    'county assessor', 'county sheriff', 'deputy sheriff', 'constable'
]

CITY_OFFICIALS = [
    'city manager', 'town manager', 'city council member', 'alderman', 'alderwoman',
    'city attorney', 'city auditor', 'city comptroller', 'police chief', 'deputy police chief',
    'fire chief', 'fire commissioner', 'mayor', 'city council'
]

ALL_OFFICIALS = FEDERAL_OFFICIALS + STATE_OFFICIALS + COUNTY_OFFICIALS + CITY_OFFICIALS

# EXCLUDE KEYWORDS - Non-officials
EXCLUDE_KEYWORDS = [
    'gang member', 'drug dealer', 'felon', 'suspect', 'businessman',
    'activist', 'citizen', 'resident', 'defendant', 'private citizen',
    'business owner', 'contractor', 'employee', 'worker'
]

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty', 'indicted', 'charged', 'corruption', 'bribery',
    'fraud', 'removed', 'suspended', 'sentenced', 'plea', 'conspiracy',
    'embezzle', 'theft', 'abuse', 'illegal', 'misconduct', 'crime', 'criminal'
]

def get_official_level(text):
    text_lower = text.lower()
    
    if any(kw in text_lower for kw in FEDERAL_OFFICIALS):
        return 'Federal'
    elif any(kw in text_lower for kw in STATE_OFFICIALS):
        return 'State'
    elif any(kw in text_lower for kw in COUNTY_OFFICIALS):
        return 'County'
    elif any(kw in text_lower for kw in CITY_OFFICIALS):
        return 'City'
    return None

def is_public_official(text):
    text_lower = text.lower()
    
    # Must contain an official keyword
    has_official = any(kw in text_lower for kw in ALL_OFFICIALS)
    if not has_official:
        return False
    
    # Must NOT contain exclude keywords
    has_exclude = any(kw in text_lower for kw in EXCLUDE_KEYWORDS)
    if has_exclude:
        return False
    
    # Must contain misconduct keyword
    has_misconduct = any(kw in text_lower for kw in MISCONDUCT_KEYWORDS)
    if not has_misconduct:
        return False
    
    return True

def get_position(text):
    text_lower = text.lower()
    
    if 'president' in text_lower and 'vice' not in text_lower:
        return 'President'
    elif 'vice president' in text_lower:
        return 'Vice President'
    elif 'cabinet' in text_lower:
        return 'Cabinet Secretary'
    elif 'senator' in text_lower:
        return 'Senator'
    elif 'congressman' in text_lower or 'congresswoman' in text_lower:
        return 'Congressman'
    elif 'federal judge' in text_lower:
        return 'Federal Judge'
    elif 'u.s. attorney' in text_lower or 'us attorney' in text_lower:
        return 'U.S. Attorney'
    elif 'federal prosecutor' in text_lower:
        return 'Federal Prosecutor'
    elif 'fbi agent' in text_lower:
        return 'FBI Agent'
    elif 'dea agent' in text_lower:
        return 'DEA Agent'
    elif 'lieutenant governor' in text_lower:
        return 'Lieutenant Governor'
    elif 'governor' in text_lower:
        return 'Governor'
    elif 'state senator' in text_lower:
        return 'State Senator'
    elif 'state representative' in text_lower:
        return 'State Representative'
    elif 'state judge' in text_lower:
        return 'State Judge'
    elif 'state attorney general' in text_lower or 'state ag' in text_lower:
        return 'State Attorney General'
    elif 'state treasurer' in text_lower:
        return 'State Treasurer'
    elif 'state auditor' in text_lower:
        return 'State Auditor'
    elif 'state trooper' in text_lower or 'state police' in text_lower:
        return 'State Police Officer'
    elif 'county commissioner' in text_lower:
        return 'County Commissioner'
    elif 'county judge' in text_lower:
        return 'County Judge'
    elif 'county clerk' in text_lower:
        return 'County Clerk'
    elif 'district attorney' in text_lower:
        return 'District Attorney'
    elif 'county attorney' in text_lower:
        return 'County Attorney'
    elif 'county auditor' in text_lower:
        return 'County Auditor'
    elif 'county treasurer' in text_lower:
        return 'County Treasurer'
    elif 'county sheriff' in text_lower or 'sheriff' in text_lower:
        return 'Sheriff'
    elif 'deputy sheriff' in text_lower:
        return 'Deputy Sheriff'
    elif 'constable' in text_lower:
        return 'Constable'
    elif 'city manager' in text_lower or 'town manager' in text_lower:
        return 'City Manager'
    elif 'city council' in text_lower:
        return 'City Council Member'
    elif 'alderman' in text_lower or 'alderwoman' in text_lower:
        return 'Alderman'
    elif 'city attorney' in text_lower:
        return 'City Attorney'
    elif 'city auditor' in text_lower:
        return 'City Auditor'
    elif 'city comptroller' in text_lower:
        return 'City Comptroller'
    elif 'police chief' in text_lower:
        return 'Police Chief'
    elif 'fire chief' in text_lower or 'fire commissioner' in text_lower:
        return 'Fire Chief'
    elif 'mayor' in text_lower:
        return 'Mayor'
    elif 'police' in text_lower or 'officer' in text_lower:
        return 'Police Officer'
    
    return 'Public Official'

def get_status(text):
    text_lower = text.lower()
    if 'convicted' in text_lower or 'guilty plea' in text_lower or 'guilty' in text_lower:
        return 'Convicted'
    elif 'indicted' in text_lower or 'grand jury' in text_lower:
        return 'Indicted'
    elif 'charged' in text_lower and 'convicted' not in text_lower:
        return 'Indicted'
    elif 'dismissed' in text_lower:
        return 'Dismissed'
    elif 'acquitted' in text_lower:
        return 'Acquitted'
    else:
        return 'Convicted'

def get_name(title):
    title = re.sub(r'^(Former|Retired|Ex-)\s+', '', title, flags=re.IGNORECASE)
    if ' - ' in title:
        name = title.split(' - ')[0].strip()
        if 3 < len(name) < 150:
            return name[:100]
    for verb in ['Convicted', 'Charged', 'Indicted', 'Sentenced', 'Plead']:
        if verb in title:
            return title.split(verb)[0].strip()[:100]
    return 'Unknown Official'

def scrape_doj_api(search_term):
    cases = []
    
    try:
        url = 'https://www.justice.gov/api/v1/press_releases.json'
        params = {
            'limit': 100,
            'title': search_term
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return cases
        
        data = response.json()
        releases = data.get('results', [])
        
        for release in releases:
            try:
                title = release.get('title', '').strip()
                body = release.get('body', '').strip()
                url = release.get('url', '')
                
                if not title or not body:
                    continue
                
                combined = f"{title} {body}"
                
                if not is_public_official(combined):
                    continue
                
                full_name = get_name(title)
                level = get_official_level(combined)
                
                if not level:
                    continue
                
                case = {
                    'full_name': full_name,
                    'title': title[:150],
                    'position_title': get_position(combined),
                    'official_type': 'Judicial' if 'judge' in combined.lower() else 'Executive' if any(x in combined.lower() for x in ['mayor', 'governor', 'director', 'commissioner']) else 'Law Enforcement' if 'police' in combined.lower() or 'sheriff' in combined.lower() else 'Legislative',
                    'location': 'Unknown',
                    'level': level,
                    'category': 'Corruption',
                    'abuse_of_power_type': 'Corruption',
                    'case_status': get_status(combined),
                    'details': body[:1000],
                    'source_url': url,
                    'source_type': 'court_record',
                    'source_date': str(datetime.now().date()),
                    'publication_status': 'draft',
                    'verified_by': 'comprehensive_scraper',
                    'verified_at': datetime.now().isoformat(),
                    'fingerprint': hashlib.md5(f"{title}_{url}".encode()).hexdigest()[:16]
                }
                
                cases.append(case)
            except:
                continue
        
        return cases
    
    except Exception as e:
        print(f"  Error: {str(e)[:60]}")
        return cases

def scrape_all_official_types():
    print("\n" + "="*70)
    print("FEDERAL OFFICIAL SCRAPER - STRICT VALIDATION")
    print("="*70 + "\n")
    
    search_terms = [
        'federal judge convicted', 'federal judge indicted', 'u.s. attorney charged',
        'senator guilty', 'senator convicted', 'senator indicted',
        'congressman convicted', 'congressman indicted', 'congressman guilty',
        'representative convicted', 'representative indicted',
        'federal prosecutor indicted', 'fbi agent convicted', 'fbi agent indicted',
        'cabinet secretary convicted', 'cabinet convicted',
        'state judge convicted', 'state judge indicted', 'state attorney general charged',
        'state senator guilty', 'state representative convicted',
        'governor convicted', 'governor indicted', 'governor guilty',
        'state treasurer convicted', 'state auditor indicted',
        'county commissioner convicted', 'county judge charged', 'district attorney guilty',
        'county sheriff indicted', 'sheriff convicted', 'sheriff indicted',
        'county attorney charged',
        'mayor convicted', 'mayor indicted', 'city council guilty',
        'police chief indicted', 'fire chief convicted',
        'city attorney charged', 'alderman guilty'
    ]
    
    all_cases = []
    
    for term in search_terms:
        print(f"  Searching: {term:40}", end='', flush=True)
        cases = scrape_doj_api(term)
        all_cases.extend(cases)
        print(f" Found: {len(cases)}")
        time.sleep(0.5)
    
    return all_cases

def upload_to_supabase(cases):
    if not cases:
        print("\nNo cases to upload")
        return 0
    
    print(f"\n" + "="*70)
    print(f"Total scraped: {len(cases)}")
    
    statuses = {}
    positions = {}
    levels = {}
    
    for c in cases:
        statuses[c['case_status']] = statuses.get(c['case_status'], 0) + 1
        positions[c['position_title']] = positions.get(c['position_title'], 0) + 1
        levels[c['level']] = levels.get(c['level'], 0) + 1
    
    print("\nBy Status:")
    for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count}")
    
    print("\nTop Positions:")
    for position, count in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {position}: {count}")
    
    print("\nBy Level:")
    for level, count in sorted(levels.items(), key=lambda x: x[1], reverse=True):
        print(f"  {level}: {count}")
    
    with open('comprehensive_strict_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved: comprehensive_strict_cases.json")
    
    print(f"\n" + "="*70)
    print("Deduplicating and uploading...")
    
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        resp = supabase.table('cases').select('fingerprint').execute()
        existing_fps = {row['fingerprint'] for row in resp.data}
        print(f"  Existing in DB: {len(existing_fps)}")
        
        new_cases = [c for c in cases if c['fingerprint'] not in existing_fps]
        print(f"  New cases found: {len(new_cases)}")
        print(f"  Duplicates filtered: {len(cases) - len(new_cases)}")
        
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
    cases = scrape_all_official_types()
    uploaded = upload_to_supabase(cases)
    
    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} new cases uploaded (STRICT validation)")
    print("="*70 + "\n")