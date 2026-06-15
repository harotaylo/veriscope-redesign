#!/usr/bin/env python3
"""
Modular state court scraper framework.
Each state has different court systems, so we use state-specific handlers.
"""
import json
import requests
import hashlib
import re
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
    match = re.search(r'(Judge|Magistrate|Sheriff|Prosecutor|Attorney|Official|Chief|Director)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', text)
    if match:
        return match.group(2)[:100]
    words = text.split()
    if len(words) >= 2:
        return ' '.join(words[:2])[:100]
    return 'Unknown Official'

class StateCourtScraper(ABC):
    """Base class for state-specific court scrapers."""

    def __init__(self, state_code, state_name):
        self.state_code = state_code
        self.state_name = state_name
        self.cases = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    @abstractmethod
    def scrape(self):
        """Override to implement state-specific scraping logic."""
        pass

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
            'verified_by': 'state_court_scraper',
            'verified_at': datetime.now().isoformat(),
            'fingerprint': hashlib.md5((title + source_url).encode()).hexdigest()[:16]
        }
        self.cases.append(case)

class CaliforniaScraper(StateCourtScraper):
    """California courts - uses case management system."""

    def scrape(self):
        print(f"  Scraping {self.state_name} courts...")
        # California CLETS (Case and Arrest Record System) - requires specific queries
        # For now, use state AG press releases as fallback
        self._scrape_ag_press_releases()
        return self.cases

    def _scrape_ag_press_releases(self):
        """Fallback to California AG press releases."""
        try:
            url = 'https://oag.ca.gov/news'
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                articles = soup.find_all('a', {'class': 'news-item'})[:20]
                for article in articles:
                    title = article.get_text().strip()
                    link = article.get('href', '')
                    if any(kw in title.lower() for kw in ['convicted', 'charged', 'indicted', 'sentenced', 'guilty']):
                        self.add_case(title, None, None, None, title, link)
        except Exception as e:
            print(f"    Error: {str(e)[:40]}")

class TexasScraper(StateCourtScraper):
    """Texas courts - uses TXCOURTS system."""

    def scrape(self):
        print(f"  Scraping {self.state_name} courts...")
        self._scrape_ag_press_releases()
        return self.cases

    def _scrape_ag_press_releases(self):
        """Texas AG press releases."""
        try:
            url = 'https://www.texasattorneygeneral.gov/news'
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                articles = soup.find_all('a', class_='news-link')[:20]
                for article in articles:
                    title = article.get_text().strip()
                    link = article.get('href', '')
                    if any(kw in title.lower() for kw in ['convicted', 'charged', 'indicted', 'sentenced']):
                        self.add_case(title, None, None, None, title, link)
        except Exception as e:
            print(f"    Error: {str(e)[:40]}")

class FloridaScraper(StateCourtScraper):
    """Florida courts."""

    def scrape(self):
        print(f"  Scraping {self.state_name} courts...")
        self._scrape_ag_press_releases()
        return self.cases

    def _scrape_ag_press_releases(self):
        """Florida AG press releases."""
        try:
            url = 'https://www.myfloridalegal.com/news'
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                articles = soup.find_all('div', class_='article')[:20]
                for article in articles:
                    title = article.get_text().strip()
                    link = article.find('a')
                    link = link.get('href', '') if link else ''
                    if any(kw in title.lower() for kw in ['convicted', 'charged', 'indicted']):
                        self.add_case(title, None, None, None, title, link)
        except Exception as e:
            print(f"    Error: {str(e)[:40]}")

class NewYorkScraper(StateCourtScraper):
    """New York courts."""

    def scrape(self):
        print(f"  Scraping {self.state_name} courts...")
        self._scrape_ag_press_releases()
        return self.cases

    def _scrape_ag_press_releases(self):
        """New York AG press releases."""
        try:
            url = 'https://ag.ny.gov/press-releases'
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                articles = soup.find_all('a', class_='press-release-link')[:20]
                for article in articles:
                    title = article.get_text().strip()
                    link = article.get('href', '')
                    if any(kw in title.lower() for kw in ['convicted', 'charged', 'indicted']):
                        self.add_case(title, None, None, None, title, link)
        except Exception as e:
            print(f"    Error: {str(e)[:40]}")

class PennsylvaniaScraper(StateCourtScraper):
    """Pennsylvania courts."""

    def scrape(self):
        print(f"  Scraping {self.state_name} courts...")
        self._scrape_ag_press_releases()
        return self.cases

    def _scrape_ag_press_releases(self):
        """Pennsylvania AG press releases."""
        try:
            url = 'https://www.attorneygeneral.gov/news/'
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, 'html.parser')
                articles = soup.find_all('a', class_='news-item')[:20]
                for article in articles:
                    title = article.get_text().strip()
                    link = article.get('href', '')
                    if any(kw in title.lower() for kw in ['convicted', 'charged', 'indicted']):
                        self.add_case(title, None, None, None, title, link)
        except Exception as e:
            print(f"    Error: {str(e)[:40]}")

# Map state codes to scraper classes
STATE_SCRAPERS = {
    'CA': CaliforniaScraper,
    'TX': TexasScraper,
    'FL': FloridaScraper,
    'NY': NewYorkScraper,
    'PA': PennsylvaniaScraper,
}

STATE_NAMES = {
    'CA': 'California', 'TX': 'Texas', 'FL': 'Florida', 'NY': 'New York',
    'PA': 'Pennsylvania', 'IL': 'Illinois', 'OH': 'Ohio', 'GA': 'Georgia',
    'NC': 'North Carolina', 'MI': 'Michigan', 'NJ': 'New Jersey',
    'VA': 'Virginia', 'WA': 'Washington', 'AZ': 'Arizona', 'MA': 'Massachusetts'
}

def scrape_state_courts():
    print("\n" + "="*70)
    print("VeriScope - State Courts Scraper (Tier 1)")
    print("="*70)

    all_cases = []
    for state_code, state_name in STATE_NAMES.items():
        try:
            if state_code in STATE_SCRAPERS:
                scraper_class = STATE_SCRAPERS[state_code]
            else:
                # Use generic scraper for states without specific implementation
                scraper_class = StateCourtScraper

            scraper = scraper_class(state_code, state_name)
            cases = scraper.scrape()
            all_cases.extend(cases)
            print(f"    Found: {len(cases)} cases")
        except Exception as e:
            print(f"    Error: {str(e)[:60]}")

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
    for location, count in sorted(locations.items(), key=lambda x: x[1], reverse=True):
        print(f"  {location}: {count}")

    with open('state_cases_tier1.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved: state_cases_tier1.json")

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
    cases = scrape_state_courts()
    uploaded = upload_to_supabase(cases)
    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} new cases uploaded")
    print("="*70 + "\n")
