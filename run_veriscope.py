#!/usr/bin/env python3
import json, requests, hashlib
from datetime import datetime

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

VALID_STATUS = ['Indicted', 'Convicted', 'Acquitted', 'Dismissed']

# RELAXED: Include more variations
OFFICIAL_KEYWORDS = [
    'judge', 'senator', 'representative', 'congressman', 'congresswoman',
    'federal', 'u.s. attorney', 'fbi', 'official', 'governor', 'mayor',
    'police', 'sheriff', 'officer', 'commissioner', 'director', 'chief',
    'administrator', 'supervisor', 'manager', 'contractor', 'consultant',
    'government', 'state', 'county', 'city', 'agency', 'department'
]

# RELAXED: More misconduct variations
MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty', 'indicted', 'charged', 'corruption', 'bribery',
    'fraud', 'removed', 'suspended', 'resign', 'sentenced', 'prison',
    'plea', 'conspiracy', 'embezzle', 'money laundering', 'theft', 'assault',
    'abuse', 'neglect', 'violation', 'misconduct', 'illegal', 'crime'
]

def map_status(status):
    if status == 'Charged':
        return 'Indicted'
    elif status == 'Suspended' or status == 'Removed':
        return 'Dismissed'
    else:
        return status if status in VALID_STATUS else 'Indicted'

def scrape_doj():
    """Scrape DOJ with relaxed filtering"""
    print("\n" + "="*60)
    print("Scraping DOJ (Relaxed Filtering)")
    print("="*60 + "\n")
    
    cases = []
    url = "https://www.justice.gov/api/v1/press_releases.json"
    
    # BROADER searches
    searches = [
        'convicted',
        'indicted',
        'sentenced',
        'official guilty',
        'government fraud',
        'corruption',
        'bribery',
        'plea guilty',
        'federal charges'
    ]
    
    for search_term in searches:
        print(f"Searching: '{search_term}'")
        
        params = {
            'parameters[title]': search_term,
            'page': 0,
            'pagesize': 50  # Get more results per search
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                continue
            
            data = resp.json()
            results = data.get('results', [])
            print(f"  Found {len(results)} results")
            
            for result in results:
                title = result.get('title', '')
                body = result.get('body', '')
                url_item = result.get('url', '')
                
                # RELAXED: Accept even if we can't extract a clear name
                full_name = 'Unknown Official'
                if ' - ' in title:
                    parts = title.split(' - ')
                    if len(parts[0]) > 2:  # Lowered from 3
                        full_name = parts[0].strip()[:100]
                
                combined_text = f"{title} {body}".lower()
                
                # RELAXED: Only check if it has ANY official/misconduct keywords
                has_official = any(kw in combined_text for kw in OFFICIAL_KEYWORDS)
                has_misconduct = any(kw in combined_text for kw in MISCONDUCT_KEYWORDS)
                
                # RELAXED: Accept if it has either official OR misconduct keyword (not strict AND)
                if not (has_official or has_misconduct):
                    continue
                
                # Determine status
                case_status = 'Convicted'
                if 'indicted' in combined_text:
                    case_status = 'Indicted'
                elif 'charged' in combined_text and 'convicted' not in combined_text:
                    case_status = 'Charged'
                elif 'acquitted' in combined_text or 'not guilty' in combined_text:
                    case_status = 'Acquitted'
                elif 'dismissed' in combined_text:
                    case_status = 'Dismissed'
                
                case_status = map_status(case_status)
                
                case = {
                    'full_name': full_name,
                    'title': title[:150],
                    'position_title': 'Official',
                    'official_type': 'Executive',
                    'location': 'Federal',
                    'level': 'Federal',
                    'category': 'Corruption',
                    'abuse_of_power_type': 'Corruption',
                    'case_status': case_status,
                    'details': body[:1000],
                    'source_url': url_item,
                    'source_type': 'court_record',
                    'source_date': str(datetime.now().date()),
                    'publication_status': 'draft',
                    'verified_by': 'doj_scraper',
                    'verified_at': datetime.now().isoformat()
                }
                
                fp_text = url_item if url_item else f"{title}_{case_status}"
                case['fingerprint'] = hashlib.md5(fp_text.encode()).hexdigest()[:16]
                
                cases.append(case)
                print(f"    [+] {title[:50]}...")
        
        except Exception as e:
            continue
    
    return cases

def dedup_and_upload(cases):
    """Deduplicate and upload"""
    if not cases:
        print("No cases to upload")
        return 0
    
    print(f"\nChecking for duplicates...")
    
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        print("  Fetching existing fingerprints...")
        existing = supabase.table('cases').select('fingerprint').execute()
        existing_fps = {row['fingerprint'] for row in existing.data}
        print(f"  Found {len(existing_fps)} existing fingerprints")
        
        new_cases = [c for c in cases if c['fingerprint'] not in existing_fps]
        duplicates = len(cases) - len(new_cases)
        
        print(f"  New cases: {len(new_cases)}")
        print(f"  Duplicates filtered: {duplicates}")
        
        if not new_cases:
            print("  All cases already in database!")
            return 0
        
        print(f"\nUploading {len(new_cases)} new cases...")
        uploaded_count = 0
        
        for i in range(0, len(new_cases), 50):
            chunk = new_cases[i:i+50]
            try:
                supabase.table('cases').insert(chunk).execute()
                uploaded_count += len(chunk)
                print(f"  [+] Uploaded {uploaded_count}/{len(new_cases)}")
            except Exception as e:
                print(f"  Error: {str(e)[:80]}")
        
        return uploaded_count
    
    except ImportError:
        with open('veriscope_cases.json', 'w') as f:
            json.dump(cases, f, indent=2)
        return 0

if __name__ == '__main__':
    print("\n" + "="*60)
    print("VeriScope - Relaxed Filter")
    print("="*60)
    
    cases = scrape_doj()
    
    if cases:
        print(f"\nTotal cases scraped: {len(cases)}")
        
        status_counts = {}
        for case in cases:
            status = case.get('case_status')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\nStatus Distribution:")
        for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {status}: {count}")
        
        with open('veriscope_cases.json', 'w') as f:
            json.dump(cases, f, indent=2)
        print("\nSaved to veriscope_cases.json")
        
        uploaded = dedup_and_upload(cases)
        print(f"\nSuccessfully uploaded: {uploaded} NEW cases")
    
    print("="*60 + "\n")