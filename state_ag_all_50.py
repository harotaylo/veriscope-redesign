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

STATE_AG_URLS = {
    'AL': 'https://ago.alabama.gov/news-media/news-releases/',
    'AK': 'https://law.alaska.gov/news/',
    'AZ': 'https://azag.gov/press-releases',
    'AR': 'https://ago.arkansas.gov/news-and-media/news-releases',
    'CA': 'https://oag.ca.gov/news',
    'CO': 'https://coag.gov/press-releases',
    'CT': 'https://portal.ct.gov/AG/Press-Release',
    'DE': 'https://dnrec.delaware.gov/air/permits/news/',
    'FL': 'https://www.myfloridalegal.com/news-releases',
    'GA': 'https://law.georgia.gov/news',
    'HI': 'https://ag.hawaii.gov/news-releases/',
    'ID': 'https://ag.idaho.gov/news-media/news-releases/',
    'IL': 'https://www2.illinois.gov/Pages/news-releases.aspx',
    'IN': 'https://www.in.gov/attorney-general/news/',
    'IA': 'https://sos.iowa.gov/search/all',
    'KS': 'https://ag.ks.gov/news',
    'KY': 'https://ag.ky.gov/news-media/news-releases',
    'LA': 'https://www.ag.louisiana.gov/news',
    'ME': 'https://www.maine.gov/ag/news',
    'MD': 'https://mta.maryland.gov/news-room',
    'MA': 'https://www.mass.gov/news',
    'MI': 'https://www.michigan.gov/ag/news',
    'MN': 'https://www.ag.state.mn.us/office/news',
    'MS': 'https://www.ago.ms.gov/news-and-media',
    'MO': 'https://ago.mo.gov/news-and-media',
    'MT': 'https://doj.mt.gov/news',
    'NE': 'https://www.ago.ne.gov/media_releases.html',
    'NV': 'https://ag.nv.gov/news',
    'NH': 'https://www.doj.nh.gov/news-and-media',
    'NJ': 'https://www.nj.gov/oag/newsreleases/',
    'NM': 'https://www.nmag.gov/news/',
    'NY': 'https://ag.ny.gov/press-release',
    'NC': 'https://ncdoj.gov/news',
    'ND': 'https://www.ag.nd.gov/news',
    'OH': 'https://www.ohioattorneygeneral.gov/news',
    'OK': 'https://www.oag.ok.gov/newsroom',
    'OR': 'https://www.oregon.gov/ag/pages/news.aspx',
    'PA': 'https://www.attorneygeneral.gov/news/',
    'RI': 'https://ag.ri.gov/news-and-alerts',
    'SC': 'https://www.scag.gov/news-and-public-information/',
    'SD': 'https://atg.sd.gov/news',
    'TN': 'https://www.tn.gov/attorneygeneral/news.html',
    'TX': 'https://www.texasattorneygeneral.gov/news-releases',
    'UT': 'https://www.attorneygeneral.gov/newsroom/',
    'VT': 'https://ago.vermont.gov/latest-news',
    'VA': 'https://www.oag.state.va.us/news',
    'WA': 'https://www.atg.wa.gov/news-media',
    'WV': 'https://www.ag.wv.gov/news',
    'WI': 'https://www.doj.state.wi.us/news',
    'WY': 'https://ag.wyo.gov/press-releases'
}

POSITION_MAP = {
    'judge': 'Judge', 'senator': 'Senator', 'representative': 'Representative',
    'governor': 'Governor', 'mayor': 'Mayor', 'sheriff': 'Sheriff',
    'police': 'Police Officer', 'commissioner': 'Commissioner',
    'director': 'Director', 'chief': 'Chief', 'attorney': 'Attorney General',
    'officer': 'Officer', 'prosecutor': 'Prosecutor', 'official': 'Official'
}

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty', 'indicted', 'charged', 'corruption', 'bribery',
    'fraud', 'removed', 'suspended', 'sentenced', 'plea', 'conspiracy',
    'embezzle', 'theft', 'abuse', 'illegal', 'misconduct', 'crime'
]

def get_position(text):
    text_lower = text.lower()
    for keyword, position in POSITION_MAP.items():
        if keyword in text_lower:
            return position
    return 'Official'

def get_status(text):
    text_lower = text.lower()
    if 'convicted' in text_lower or 'guilty plea' in text_lower:
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
    for verb in ['Convicted', 'Charged', 'Indicted', 'Sentenced']:
        if verb in title:
            return title.split(verb)[0].strip()[:100]
    return 'Unknown Official'

def scrape_state_ag(state_code, url):
    cases = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url, timeout=10, headers=headers)
        
        if resp.status_code != 200:
            return cases
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        selectors = [
            'article', 'div.news-item', 'div.press-release',
            'div.news-release', 'div.release', 'li.news',
            'div[class*="news"]', 'div[class*="press"]',
            'div[class*="release"]', 'a[href*="press"]'
        ]
        
        articles = []
        for selector in selectors:
            articles.extend(soup.select(selector))
        
        articles = articles[:50]
        
        for article in articles:
            try:
                title_elem = article.find(['h2', 'h3', 'h4', 'a', 'span'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                if len(title) < 10:
                    continue
                
                body_elem = article.find(['p', 'div.summary', 'div[class*="desc"]'])
                body = body_elem.get_text(strip=True) if body_elem else ""
                
                combined = f"{title} {body}".lower()
                has_misconduct = any(kw in combined for kw in MISCONDUCT_KEYWORDS)
                has_official = any(w in combined for w in ['official', 'judge', 'mayor', 'sheriff', 'police', 'director', 'commissioner', 'attorney'])
                
                if not (has_misconduct and has_official):
                    continue
                
                full_name = get_name(title)
                case = {
                    'full_name': full_name,
                    'title': title[:150],
                    'position_title': get_position(combined),
                    'official_type': 'Executive',
                    'location': state_code,
                    'level': 'State',
                    'category': 'Corruption',
                    'abuse_of_power_type': 'Corruption',
                    'case_status': get_status(combined),
                    'details': body[:1000],
                    'source_url': url,
                    'source_type': 'court_record',
                    'source_date': str(datetime.now().date()),
                    'publication_status': 'draft',
                    'verified_by': 'state_ag_scraper',
                    'verified_at': datetime.now().isoformat(),
                    'fingerprint': hashlib.md5(f"{title}_{state_code}".encode()).hexdigest()[:16]
                }
                
                cases.append(case)
            except:
                continue
        
        return cases
    except Exception as e:
        return cases

def scrape_all_states():
    print("\n" + "="*70)
    print("STATE ATTORNEY GENERAL SCRAPER - All 50 States")
    print("="*70 + "\n")
    
    all_cases = []
    
    for state_code, url in STATE_AG_URLS.items():
        print(f"  {state_code}: {url[:50]:50}", end='', flush=True)
        
        cases = scrape_state_ag(state_code, url)
        all_cases.extend(cases)
        
        print(f" Found: {len(cases)}")
        time.sleep(1)
    
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
    for position, count in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {position}: {count}")
    
    print("\nStates with Cases:")
    for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True):
        print(f"  {location}: {count}")
    
    with open('state_ag_all_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved: state_ag_all_cases.json")
    
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
    cases = scrape_all_states()
    uploaded = upload_to_supabase(cases)
    
    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} new state AG cases uploaded")
    print("="*70 + "\n")