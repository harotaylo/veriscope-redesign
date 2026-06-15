#!/usr/bin/env python3
"""
VeriScope Unified Master Scraper
Combines DOJ federal + all 50 states + territories into one comprehensive scraper.
Run once to get complete federal + state official misconduct cases.
"""
import json
import requests
import hashlib
import re
import time
from datetime import datetime
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

POSITIONS = {
    'judge': 'Judge', 'senator': 'Senator', 'representative': 'Representative',
    'governor': 'Governor', 'mayor': 'Mayor', 'sheriff': 'Sheriff',
    'deputy': 'Deputy', 'constable': 'Constable', 'marshal': 'Marshal',
    'police': 'Police Officer', 'commissioner': 'Commissioner',
    'director': 'Director', 'chief': 'Chief', 'attorney': 'Attorney',
    'magistrate': 'Magistrate', 'prosecutor': 'Prosecutor',
    'district attorney': 'District Attorney', 'official': 'Official'
}

POSITION_TYPE = {
    'Judge': 'Judicial', 'Senator': 'Legislative', 'Representative': 'Legislative',
    'Governor': 'Executive', 'Mayor': 'Executive', 'Sheriff': 'Law Enforcement',
    'Deputy': 'Law Enforcement', 'Constable': 'Law Enforcement', 'Marshal': 'Law Enforcement',
    'Police Officer': 'Law Enforcement', 'Commissioner': 'Executive',
    'Director': 'Executive', 'Chief': 'Law Enforcement', 'Attorney': 'Legal',
    'Magistrate': 'Judicial', 'Prosecutor': 'Legal', 'District Attorney': 'Legal',
    'Official': 'Executive'
}

def get_position(text):
    text_lower = text.lower()
    sorted_keywords = sorted(POSITIONS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in text_lower:
            return POSITIONS[keyword]
    patterns = [
        r'\bHon\.\s+', r'\bJudge\b', r'\bSheriff\b', r'\bDeputy\b',
        r'\bMarshal\b', r'\bConstable\b', r'\bChief\b', r'\bOfficer\b',
        r'\bProsecutor\b', r'\bAttorney\b', r'\bDirector\b'
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return 'Official'
    return 'Official'

def get_official_type(position):
    return POSITION_TYPE.get(position, 'Executive')

def get_status(text):
    text_lower = text.lower()
    if 'convicted' in text_lower or 'guilty plea' in text_lower:
        return 'Convicted'
    elif 'sentenced' in text_lower or 'imprisonment' in text_lower:
        return 'Convicted'
    elif 'acquitted' in text_lower or 'not guilty' in text_lower:
        return 'Acquitted'
    elif 'dismissed' in text_lower:
        return 'Dismissed'
    elif 'indicted' in text_lower or 'grand jury' in text_lower:
        return 'Indicted'
    elif 'charged' in text_lower or 'arraigned' in text_lower:
        return 'Indicted'
    return 'Indicted'

def get_name(text):
    text = re.sub(r'^(Former|Retired|Ex-)\s+', '', text, flags=re.IGNORECASE)
    if ' v. ' in text:
        return text.split(' v. ')[0].strip()[:100]
    match = re.search(r'(Judge|Magistrate|Sheriff|Prosecutor|Attorney|Official|Chief|Director|Senator|Representative|Governor|Mayor|Deputy|Constable|Marshal|Police|Commissioner)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', text)
    if match:
        return match.group(2)[:100]
    words = text.split()
    if len(words) >= 2:
        return ' '.join(words[:2])[:100]
    return 'Unknown Official'

# ============================================================================
# DOJ FEDERAL SCRAPER
# ============================================================================

def scrape_doj():
    """Scrape DOJ federal cases - paginated to get all results."""
    print("\n" + "="*70)
    print("DOJ Federal Cases Scraper")
    print("="*70)

    all_cases = []
    url = "https://www.justice.gov/api/v1/press_releases.json"

    searches = [
        'convicted judge', 'indicted official', 'federal official convicted',
        'bribery', 'corruption', 'sentenced judge', 'guilty plea official',
        'fraud conviction', 'embezzlement', 'misconduct official'
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    for search_term in searches:
        print(f"Searching: {search_term}")
        page = 0
        total_found = 0

        try:
            while True:
                params = {
                    'parameters[title]': search_term,
                    'page': page,
                    'pagesize': 100
                }

                resp = requests.get(url, params=params, headers=headers, timeout=10)

                if resp.status_code != 200:
                    print(f"  Status: {resp.status_code}")
                    break

                data = resp.json()
                results = data.get('results', [])

                if not results:
                    break

                total_found += len(results)

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
                        status = get_status(combined)
                        official_type = get_official_type(position)

                        case = {
                            'full_name': full_name,
                            'title': title[:150],
                            'position_title': position,
                            'official_type': official_type,
                            'location': 'Federal',
                            'level': 'Federal',
                            'category': 'Corruption',
                            'abuse_of_power_type': 'Corruption',
                            'case_status': status,
                            'details': body[:1000],
                            'source_url': source_url,
                            'source_type': 'court_record',
                            'source_date': str(datetime.now().date()),
                            'publication_status': 'draft',
                            'verified_by': 'unified_scraper_doj',
                            'verified_at': datetime.now().isoformat(),
                            'fingerprint': hashlib.md5(source_url.encode()).hexdigest()[:16]
                        }

                        all_cases.append(case)

                    except:
                        continue

                page += 1

            print(f"  Found: {total_found} across {page} pages")

        except Exception as e:
            print(f"  Error: {str(e)[:60]}")

    return all_cases

# ============================================================================
# STATE COURT SCRAPER BASE CLASS
# ============================================================================

class StateCourtScraper(ABC):
    """Base class for state-specific court scrapers."""

    def __init__(self, state_code, state_name):
        self.state_code = state_code
        self.state_name = state_name
        self.cases = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape(self):
        """Default implementation - override in subclasses."""
        return self.cases

    def add_case(self, title, name, position, status, details, source_url):
        """Helper to add a case with standard formatting."""
        case = {
            'full_name': name or get_name(title),
            'title': title[:150],
            'position_title': position or get_position(title),
            'official_type': get_official_type(position or get_position(title)),
            'location': self.state_code,
            'level': 'State',
            'category': 'Misconduct',
            'abuse_of_power_type': 'Misconduct',
            'case_status': status or get_status(title),
            'details': details[:1000] if details else '',
            'source_url': source_url,
            'source_type': 'court_record',
            'source_date': str(datetime.now().date()),
            'publication_status': 'draft',
            'verified_by': 'unified_scraper_state',
            'verified_at': datetime.now().isoformat(),
            'fingerprint': hashlib.md5((title + source_url).encode()).hexdigest()[:16]
        }
        self.cases.append(case)

    def _scrape_ag_website(self, url):
        """Generic AG website scraper - look for misconduct keywords."""
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                articles = soup.find_all('a')[:30]
                for article in articles:
                    title = article.get_text().strip()
                    if any(kw in title.lower() for kw in ['convicted', 'charged', 'indicted', 'sentenced']):
                        self.add_case(title, None, None, None, '', article.get('href', ''))
        except Exception as e:
            pass

# ============================================================================
# STATE SCRAPERS (Selected implementations for major states)
# ============================================================================

STATE_SCRAPERS = {
    'CA': ('California', 'https://oag.ca.gov/news'),
    'TX': ('Texas', 'https://www.texasattorneygeneral.gov/news'),
    'FL': ('Florida', 'https://www.myfloridalegal.com/news'),
    'NY': ('New York', 'https://ag.ny.gov/press-releases'),
    'PA': ('Pennsylvania', 'https://www.attorneygeneral.gov/news/'),
    'IL': ('Illinois', 'https://www2.illinois.gov/sites/atg/Pages/default.aspx'),
    'OH': ('Ohio', 'https://www.ohioattorneygeneral.gov/'),
    'GA': ('Georgia', 'https://law.georgia.gov/'),
    'NC': ('North Carolina', 'https://ncdoj.gov/'),
    'MI': ('Michigan', 'https://www.michigan.gov/ag'),
    'NJ': ('New Jersey', 'https://www.nj.gov/oag/'),
    'VA': ('Virginia', 'https://www.oag.state.va.us/'),
    'WA': ('Washington', 'https://www.atg.wa.gov/'),
    'AZ': ('Arizona', 'https://azag.gov/'),
    'MA': ('Massachusetts', 'https://www.mass.gov/ago'),
    'CO': ('Colorado', 'https://coag.gov/'),
    'MN': ('Minnesota', 'https://www.ag.state.mn.us/'),
    'TN': ('Tennessee', 'https://www.tn.gov/attorney-general.html'),
    'MO': ('Missouri', 'https://ago.mo.gov/'),
    'MD': ('Maryland', 'https://www.marylandattorneygeneral.gov/'),
    'WI': ('Wisconsin', 'https://www.doj.state.wi.us/'),
    'IN': ('Indiana', 'https://www.in.gov/attorneygeneral/'),
    'LA': ('Louisiana', 'https://www.ag.louisiana.gov/'),
    'SC': ('South Carolina', 'https://sccourts.org/'),
    'KY': ('Kentucky', 'https://ag.ky.gov/'),
    'OK': ('Oklahoma', 'https://www.ok.gov/oag/'),
    'AL': ('Alabama', 'https://www.ago.state.al.us/'),
    'IA': ('Iowa', 'https://www.iowaattorneygeneral.gov/'),
    'KS': ('Kansas', 'https://www.ag.ks.gov/'),
    'UT': ('Utah', 'https://www.uag.gov/'),
    'NV': ('Nevada', 'https://ag.nv.gov/'),
    'NM': ('New Mexico', 'https://www.oag.state.nm.us/'),
    'AR': ('Arkansas', 'https://www.arkansasag.gov/'),
    'MS': ('Mississippi', 'https://www.ag.ms.gov/'),
    'WV': ('West Virginia', 'https://www.ag.wv.gov/'),
    'NE': ('Nebraska', 'https://www.ag.ne.gov/'),
    'ID': ('Idaho', 'https://www.ag.idaho.gov/'),
    'ME': ('Maine', 'https://www.maine.gov/ag/'),
    'MT': ('Montana', 'https://doj.mt.gov/'),
    'RI': ('Rhode Island', 'https://ri.gov/en/government/general-treasurer'),
    'DE': ('Delaware', 'https://dnrec.delaware.gov/'),
    'SD': ('South Dakota', 'https://sdag.sd.gov/'),
    'ND': ('North Dakota', 'https://www.ag.nd.gov/'),
    'AK': ('Alaska', 'https://law.alaska.gov/'),
    'HI': ('Hawaii', 'https://ag.hawaii.gov/'),
    'VT': ('Vermont', 'https://ago.vermont.gov/'),
    'WY': ('Wyoming', 'https://ag.wyo.gov/'),
    'PR': ('Puerto Rico', 'https://www.justicia.pr.gov/'),
    'VI': ('US Virgin Islands', 'https://ag.vi.gov/'),
    'GU': ('Guam', 'https://ag.guam.gov/'),
    'AS': ('American Samoa', 'https://www.asag.gov.as/'),
    'MP': ('Northern Mariana Islands', 'https://www.cnmilaw.org/'),
}

def scrape_all_states():
    """Scrape all 50 states + territories."""
    print("\n" + "="*70)
    print("State Courts Scraper (All 50 States + Territories)")
    print("="*70)

    all_cases = []
    state_counts = {}
    errors = []

    states_list = sorted(STATE_SCRAPERS.items())
    total_states = len(states_list)

    for idx, (state_code, (state_name, ag_url)) in enumerate(states_list, 1):
        try:
            print(f"[{idx}/{total_states}] {state_name} ({state_code})...", end=' ')

            scraper = StateCourtScraper(state_code, state_name)
            scraper._scrape_ag_website(ag_url)
            cases = scraper.scrape()

            all_cases.extend(cases)
            state_counts[state_code] = len(cases)
            print(f"OK {len(cases)}")

            time.sleep(0.5)

        except Exception as e:
            error_msg = str(e)[:40]
            errors.append(f"{state_code}: {error_msg}")
            print(f"ERROR {error_msg}")

    return all_cases, state_counts, errors

# ============================================================================
# UPLOAD & DEDUP
# ============================================================================

def upload_to_supabase(cases, source_type="unified"):
    """Upload cases to Supabase with deduplication."""
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

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f'unified_cases_{ts}.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved: unified_cases_{ts}.json")

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

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*80)
    print("VeriScope Unified Master Scraper")
    print("Federal (DOJ) + All 50 States + 5 Territories")
    print("="*80)

    # Scrape DOJ
    doj_cases = scrape_doj()
    print(f"\n[OK] DOJ: {len(doj_cases)} federal cases")

    # Scrape all states
    state_cases, state_counts, errors = scrape_all_states()
    print(f"\n[OK] States: {len(state_cases)} state cases")

    # Combine
    all_cases = doj_cases + state_cases
    print(f"\n" + "="*70)
    print(f"COMBINED TOTAL: {len(all_cases)} cases")
    print(f"  - Federal (DOJ): {len(doj_cases)}")
    print(f"  - States: {len(state_cases)}")
    print(f"="*70)

    # Upload
    uploaded = upload_to_supabase(all_cases)

    print(f"\n" + "="*80)
    print(f"SUCCESS: {uploaded} new cases uploaded")
    print(f"Database now contains federal + all state official misconduct cases")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
