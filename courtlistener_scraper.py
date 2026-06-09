#!/usr/bin/env python3
import json, requests, hashlib
from datetime import datetime

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

VALID_STATUS = ['Indicted', 'Convicted', 'Acquitted', 'Dismissed']

def map_status(status):
    if status == 'Charged':
        return 'Indicted'
    elif status == 'Suspended' or status == 'Removed':
        return 'Dismissed'
    else:
        return status if status in VALID_STATUS else 'Indicted'

def extract_status(text):
    text_lower = text.lower()
    if 'indicted' in text_lower:
        return 'Indicted'
    elif 'charged' in text_lower and 'convicted' not in text_lower:
        return 'Charged'
    elif 'acquitted' in text_lower or 'not guilty' in text_lower:
        return 'Acquitted'
    elif 'dismissed' in text_lower:
        return 'Dismissed'
    elif 'convicted' in text_lower or 'guilty' in text_lower:
        return 'Convicted'
    else:
        return 'Convicted'

def scrape_courtlistener():
    print("\n" + "="*60)
    print("Scraping CourtListener API")
    print("="*60 + "\n")
    
    cases = []
    url = "https://www.courtlistener.com/api/rest/v3/opinions/"
    
    queries = [
        'convicted judge',
        'federal official convicted',
        'bribery conviction',
        'corruption official',
        'public official guilty',
        'sentenced federal',
        'plea guilty official',
        'indicted judge',
        'conspiracy conviction',
        'fraud official'
    ]
    
    for query in queries:
        print(f"Searching: '{query}'")
        
        params = {
            'q': query,
            'page': 1,
            'page_size': 100,
            'order_by': '-date_filed'
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code != 200:
                print(f"  Error: {resp.status_code}")
                continue
            
            data = resp.json()
            results = data.get('results', [])
            print(f"  Found {len(results)} results")
            
            for result in results:
                try:
                    case_name = result.get('case_name', '')
                    plain_text = result.get('plain_text', '')[:1000]
                    court = result.get('court', '')
                    url_item = result.get('absolute_url', '')
                    
                    if not case_name or len(case_name) < 5:
                        continue
                    
                    combined = f"{case_name} {plain_text}".lower()
                    
                    official_keywords = ['judge', 'official', 'federal', 'government', 'senator', 'congressman']
                    misconduct_keywords = ['convicted', 'guilty', 'indicted', 'corruption', 'bribery', 'fraud']
                    
                    has_official = any(kw in combined for kw in official_keywords)
                    has_misconduct = any(kw in combined for kw in misconduct_keywords)
                    
                    if not (has_official and has_misconduct):
                        continue
                    
                    full_name = 'Unknown Official'
                    if ' v. ' in case_name:
                        parts = case_name.split(' v. ')
                        if len(parts[0]) > 2:
                            full_name = parts[0].strip()[:100]
                    else:
                        full_name = case_name.split(',')[0][:100]
                    
                    case_status = extract_status(combined)
                    case_status = map_status(case_status)
                    
                    location = 'Federal'
                    if court:
                        if 'District' in court:
                            location = court.split('District')[0].strip()[:50]
                        elif 'Circuit' in court:
                            location = court.split('Circuit')[0].strip()[:50]
                    
                    case = {
                        'full_name': full_name,
                        'title': case_name[:150],
                        'position_title': 'Official',
                        'official_type': 'Judicial',
                        'location': location,
                        'level': 'Federal',
                        'category': 'Corruption',
                        'abuse_of_power_type': 'Corruption',
                        'case_status': case_status,
                        'details': plain_text[:1000],
                        'source_url': url_item,
                        'source_type': 'court_record',
                        'source_date': str(datetime.now().date()),
                        'publication_status': 'draft',
                        'verified_by': 'courtlistener_scraper',
                        'verified_at': datetime.now().isoformat()
                    }
                    
                    from hashlib import md5
                    fp_text = f"{case_name}_{case_status}_{location}"
                    case['fingerprint'] = md5(fp_text.encode()).hexdigest()[:16]
                    
                    cases.append(case)
                    print(f"    [+] {case_name[:60]}...")
                
                except:
                    continue
        
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    return cases

def dedup_and_upload(cases):
    if not cases:
        print("No cases to upload")
        return 0
    
    print(f"\nTotal cases from CourtListener: {len(cases)}")
    
    status_counts = {}
    for case in cases:
        status = case.get('case_status')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\nStatus Distribution:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count}")
    
    with open('courtlistener_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print("\nSaved to courtlistener_cases.json")
    
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
        print("Supabase client not available - saved to JSON only")
        return 0

if __name__ == '__main__':
    print("\n" + "="*60)
    print("CourtListener Scraper - Federal Cases")
    print("="*60)
    
    cases = scrape_courtlistener()
    uploaded = dedup_and_upload(cases)
    
    print(f"\n\nSuccessfully uploaded: {uploaded} NEW cases from CourtListener")
    print("="*60 + "\n")