#!/usr/bin/env python3
import json, requests, hashlib
from bs4 import BeautifulSoup
from datetime import datetime
import time

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

VALID_STATUS = ['Indicted', 'Convicted', 'Acquitted', 'Dismissed']

OFFICIAL_KEYWORDS = [
    'judge', 'senator', 'representative', 'congressman', 'mayor',
    'police', 'sheriff', 'officer', 'commissioner', 'director',
    'official', 'administrator', 'government'
]

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty', 'indicted', 'charged', 'corruption', 'bribery',
    'fraud', 'removed', 'suspended', 'sentenced', 'plea', 'conspiracy',
    'embezzle', 'theft', 'abuse', 'illegal', 'crime'
]

STATES = {
    'CA': 'https://oag.ca.gov/news',
    'TX': 'https://www.texasattorneygeneral.gov/news-releases',
    'FL': 'https://www.myfloridalegal.com/page/81D3BE46D5B8456B852570C5007D1234/',
    'NY': 'https://ag.ny.gov/press-release',
    'PA': 'https://www.attorneygeneral.gov/news/',
    'IL': 'https://www2.illinois.gov/Pages/news-releases.aspx',
    'OH': 'https://www.ohioattorneygeneral.gov/Individuals-and-Families/News-and-Media/Press-Releases',
    'GA': 'https://law.georgia.gov/news',
    'NC': 'https://ncdoj.gov/news',
    'MI': 'https://www.michigan.gov/ag/0,4534,7-359-82916---,00.html'
}

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

def scrape_state_ag(state_code, url):
    print(f"\n  Scraping {state_code}: {url}")
    cases = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, timeout=10, headers=headers)
        
        if resp.status_code != 200:
            print(f"    Error: {resp.status_code}")
            return cases
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        selectors = [
            'article',
            'div.news-item',
            'div.press-release',
            'div[class*="news"]',
            'div[class*="press"]',
            'li.news-item',
            'div.item',
            'a[href*="press"]'
        ]
        
        articles = []
        for selector in selectors:
            articles.extend(soup.select(selector)[:20])
        
        if not articles:
            print(f"    No articles found")
            return cases
        
        print(f"    Found {len(articles)} potential articles")
        
        for article in articles:
            try:
                title_elem = article.find(['h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if len(title) < 10:
                    continue
                
                body_elem = article.find(['p', 'div.summary', 'div[class*="desc"]'])
                body = body_elem.get_text(strip=True) if body_elem else ""
                
                combined = f"{title} {body}".lower()
                has_official = any(kw in combined for kw in OFFICIAL_KEYWORDS)
                has_misconduct = any(kw in combined for kw in MISCONDUCT_KEYWORDS)
                
                if not (has_official or has_misconduct):
                    continue
                
                full_name = 'Unknown Official'
                if ' - ' in title:
                    parts = title.split(' - ')
                    if len(parts[0]) > 2:
                        full_name = parts[0].strip()[:100]
                
                case_status = extract_status(combined)
                case_status = map_status(case_status)
                
                case = {
                    'full_name': full_name,
                    'title': title[:150],
                    'position_title': 'Official',
                    'official_type': 'Executive',
                    'location': state_code,
                    'level': 'State',
                    'category': 'Corruption',
                    'abuse_of_power_type': 'Corruption',
                    'case_status': case_status,
                    'details': body[:1000],
                    'source_url': url,
                    'source_type': 'court_record',
                    'source_date': str(datetime.now().date()),
                    'publication_status': 'draft',
                    'verified_by': 'state_ag_scraper',
                    'verified_at': datetime.now().isoformat()
                }
                
                from hashlib import md5
                fp_text = f"{title}_{state_code}_{case_status}"
                case['fingerprint'] = md5(fp_text.encode()).hexdigest()[:16]
                
                cases.append(case)
                print(f"      [+] {title[:50]}...")
            
            except:
                continue
        
        return cases
    
    except Exception as e:
        print(f"    Error: {e}")
        return cases

def scrape_all_states():
    print("\n" + "="*60)
    print("Scraping State Attorney General Press Releases")
    print("="*60)
    
    all_cases = []
    
    for state_code, url in STATES.items():
        cases = scrape_state_ag(state_code, url)
        all_cases.extend(cases)
        time.sleep(2)
    
    return all_cases

def dedup_and_upload(cases):
    if not cases:
        print("No cases to upload")
        return 0
    
    print(f"\nTotal cases from State AGs: {len(cases)}")
    
    status_counts = {}
    for case in cases:
        status = case.get('case_status')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"\nStatus Distribution:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count}")
    
    with open('state_ag_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print("\nSaved to state_ag_cases.json")
    
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
    print("State AG Scraper - Phase 1 (Top 10 States)")
    print("="*60)
    
    cases = scrape_all_states()
    uploaded = dedup_and_upload(cases)
    
    print(f"\n\nSuccessfully uploaded: {uploaded} NEW cases from State AGs")
    print("="*60 + "\n")