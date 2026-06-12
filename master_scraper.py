#!/usr/bin/env python3
"""
VeriScope Master Scraper
Combines USAO + State AG + Google RSS feeds
All 50 states + 5 territories with location extraction
"""

import json
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup
import time
from validators import CaseValidator

# Federal District Mapping
DISTRICT_MAP = {
    'NORTHERN DISTRICT OF CALIFORNIA': 'California, Northern',
    'SOUTHERN DISTRICT OF CALIFORNIA': 'California, Southern',
    'EASTERN DISTRICT OF CALIFORNIA': 'California, Eastern',
    'CENTRAL DISTRICT OF CALIFORNIA': 'California, Central',
    'NORTHERN DISTRICT OF FLORIDA': 'Florida, Northern',
    'SOUTHERN DISTRICT OF FLORIDA': 'Florida, Southern',
    'MIDDLE DISTRICT OF FLORIDA': 'Florida, Middle',
    'NORTHERN DISTRICT OF GEORGIA': 'Georgia, Northern',
    'SOUTHERN DISTRICT OF GEORGIA': 'Georgia, Southern',
    'MIDDLE DISTRICT OF GEORGIA': 'Georgia, Middle',
    'NORTHERN DISTRICT OF ILLINOIS': 'Illinois, Northern',
    'SOUTHERN DISTRICT OF ILLINOIS': 'Illinois, Southern',
    'CENTRAL DISTRICT OF ILLINOIS': 'Illinois, Central',
    'NORTHERN DISTRICT OF INDIANA': 'Indiana, Northern',
    'SOUTHERN DISTRICT OF INDIANA': 'Indiana, Southern',
    'NORTHERN DISTRICT OF IOWA': 'Iowa, Northern',
    'SOUTHERN DISTRICT OF IOWA': 'Iowa, Southern',
    'EASTERN DISTRICT OF KENTUCKY': 'Kentucky, Eastern',
    'WESTERN DISTRICT OF KENTUCKY': 'Kentucky, Western',
    'EASTERN DISTRICT OF LOUISIANA': 'Louisiana, Eastern',
    'MIDDLE DISTRICT OF LOUISIANA': 'Louisiana, Middle',
    'WESTERN DISTRICT OF LOUISIANA': 'Louisiana, Western',
    'EASTERN DISTRICT OF MICHIGAN': 'Michigan, Eastern',
    'WESTERN DISTRICT OF MICHIGAN': 'Michigan, Western',
    'NORTHERN DISTRICT OF MISSISSIPPI': 'Mississippi, Northern',
    'SOUTHERN DISTRICT OF MISSISSIPPI': 'Mississippi, Southern',
    'EASTERN DISTRICT OF MISSOURI': 'Missouri, Eastern',
    'WESTERN DISTRICT OF MISSOURI': 'Missouri, Western',
    'NORTHERN DISTRICT OF NEW YORK': 'New York, Northern',
    'SOUTHERN DISTRICT OF NEW YORK': 'New York, Southern',
    'EASTERN DISTRICT OF NEW YORK': 'New York, Eastern',
    'WESTERN DISTRICT OF NEW YORK': 'New York, Western',
    'EASTERN DISTRICT OF NORTH CAROLINA': 'North Carolina, Eastern',
    'MIDDLE DISTRICT OF NORTH CAROLINA': 'North Carolina, Middle',
    'WESTERN DISTRICT OF NORTH CAROLINA': 'North Carolina, Western',
    'NORTHERN DISTRICT OF OHIO': 'Ohio, Northern',
    'SOUTHERN DISTRICT OF OHIO': 'Ohio, Southern',
    'NORTHERN DISTRICT OF OKLAHOMA': 'Oklahoma, Northern',
    'EASTERN DISTRICT OF OKLAHOMA': 'Oklahoma, Eastern',
    'WESTERN DISTRICT OF OKLAHOMA': 'Oklahoma, Western',
    'EASTERN DISTRICT OF PENNSYLVANIA': 'Pennsylvania, Eastern',
    'MIDDLE DISTRICT OF PENNSYLVANIA': 'Pennsylvania, Middle',
    'WESTERN DISTRICT OF PENNSYLVANIA': 'Pennsylvania, Western',
    'EASTERN DISTRICT OF TENNESSEE': 'Tennessee, Eastern',
    'MIDDLE DISTRICT OF TENNESSEE': 'Tennessee, Middle',
    'WESTERN DISTRICT OF TENNESSEE': 'Tennessee, Western',
    'NORTHERN DISTRICT OF TEXAS': 'Texas, Northern',
    'SOUTHERN DISTRICT OF TEXAS': 'Texas, Southern',
    'EASTERN DISTRICT OF TEXAS': 'Texas, Eastern',
    'WESTERN DISTRICT OF TEXAS': 'Texas, Western',
    'EASTERN DISTRICT OF VIRGINIA': 'Virginia, Eastern',
    'WESTERN DISTRICT OF VIRGINIA': 'Virginia, Western',
    'EASTERN DISTRICT OF WASHINGTON': 'Washington, Eastern',
    'WESTERN DISTRICT OF WASHINGTON': 'Washington, Western',
    'NORTHERN DISTRICT OF WEST VIRGINIA': 'West Virginia, Northern',
    'SOUTHERN DISTRICT OF WEST VIRGINIA': 'West Virginia, Southern',
    'EASTERN DISTRICT OF WISCONSIN': 'Wisconsin, Eastern',
    'WESTERN DISTRICT OF WISCONSIN': 'Wisconsin, Western',
    'DISTRICT OF COLUMBIA': 'District of Columbia',
}

# All 50 States + 5 Territories
STATE_AG_URLS = {
    'Alabama': 'https://ago.alabama.gov/news-media/news-releases/',
    'Alaska': 'https://law.alaska.gov/news/',
    'Arizona': 'https://azag.gov/press-releases',
    'Arkansas': 'https://ago.arkansas.gov/news-and-media/news-releases',
    'California': 'https://oag.ca.gov/news',
    'Colorado': 'https://coag.gov/press-releases',
    'Connecticut': 'https://portal.ct.gov/AG/Press-Release',
    'Delaware': 'https://dnrec.delaware.gov/air/news/',
    'Florida': 'https://www.myfloridalegal.com/news-releases',
    'Georgia': 'https://law.georgia.gov/news',
    'Hawaii': 'https://ag.hawaii.gov/news-releases/',
    'Idaho': 'https://ag.idaho.gov/news-media/news-releases/',
    'Illinois': 'https://www.ilga.gov/commission/lrs/default.asp',
    'Indiana': 'https://www.in.gov/attorney-general/news/',
    'Iowa': 'https://ag.iowa.gov/news-releases',
    'Kansas': 'https://ag.ks.gov/news',
    'Kentucky': 'https://ag.ky.gov/news-media/news-releases',
    'Louisiana': 'https://www.ag.louisiana.gov/news',
    'Maine': 'https://www.maine.gov/ag/news',
    'Maryland': 'https://www.marylandattorneygeneral.gov/Pages/Press/default.aspx',
    'Massachusetts': 'https://www.mass.gov/orgs/office-of-the-attorney-general/news',
    'Michigan': 'https://www.michigan.gov/ag/news',
    'Minnesota': 'https://www.ag.state.mn.us/office/news',
    'Mississippi': 'https://www.ago.ms.gov/news-and-media',
    'Missouri': 'https://ago.mo.gov/news-and-media',
    'Montana': 'https://doj.mt.gov/news',
    'Nebraska': 'https://www.ne.gov/ag/news',
    'Nevada': 'https://ag.nv.gov/news/',
    'New Hampshire': 'https://www.doj.nh.gov/news/index.html',
    'New Jersey': 'https://www.nj.gov/oag/newsroom.html',
    'New Mexico': 'https://www.nmag.gov/press-releases.aspx',
    'New York': 'https://ag.ny.gov/press-release',
    'North Carolina': 'https://ncdoj.gov/news/',
    'North Dakota': 'https://www.ag.nd.gov/news',
    'Ohio': 'https://www.ohioattorneygeneral.gov/news',
    'Oklahoma': 'https://www.oag.ok.gov/news-releases',
    'Oregon': 'https://www.oregon.gov/ago/news-media/Pages/default.aspx',
    'Pennsylvania': 'https://www.attorneygeneral.gov/news-releases/',
    'Rhode Island': 'https://ag.ri.gov/news',
    'South Carolina': 'https://www.scag.gov/news-releases/',
    'South Dakota': 'https://atg.sd.gov/news-releases',
    'Tennessee': 'https://www.tn.gov/attorney-general/news.html',
    'Texas': 'https://www.texasattorneygeneral.gov/news',
    'Utah': 'https://www.attorney.utah.gov/news/',
    'Vermont': 'https://ago.vermont.gov/news-media/',
    'Virginia': 'https://www.oag.state.va.us/media-center/news-releases',
    'Washington': 'https://www.atg.wa.gov/news',
    'West Virginia': 'https://www.ag.wv.gov/News/Pages/default.aspx',
    'Wisconsin': 'https://www.doj.state.wi.us/news-room/press-releases',
    'Wyoming': 'https://ag.wyoming.gov/news-releases/',
    'District of Columbia': 'https://oag.dc.gov/news',
    'Puerto Rico': 'https://www.justicia.pr.gov/noticias/',
    'U.S. Virgin Islands': 'https://dcr.vi.gov/about-dcr',
    'Guam': 'https://www.guamag.org/news-releases/',
    'Northern Mariana Islands': 'https://www.cnmiag.org/',
    'American Samoa': 'https://www.as-ag.org/',
}

PUBLIC_OFFICIAL_KEYWORDS = [
    'judge', 'magistrate', 'senator', 'congressman', 'representative',
    'mayor', 'governor', 'sheriff', 'police officer', 'district attorney',
    'federal agent', 'fbi agent', 'dea agent', 'prosecutor', 'attorney'
]

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty', 'indicted', 'charged', 'sentenced',
    'bribery', 'extortion', 'fraud', 'corruption', 'embezzlement'
]

class MasterScraper:
    def __init__(self):
        self.cases = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_location_federal(self, text):
        """Extract USAO federal district"""
        if not text:
            return "Unknown"
        text_upper = text.upper()
        for key, value in DISTRICT_MAP.items():
            if key in text_upper:
                return value
        return "Unknown"
    
    def is_relevant(self, title, details):
        """Check if case is about public official misconduct"""
        text = (title + " " + details).lower()
        has_official = any(kw in text for kw in PUBLIC_OFFICIAL_KEYWORDS)
        has_misconduct = any(kw in text for kw in MISCONDUCT_KEYWORDS)
        return has_official and has_misconduct
    
    def scrape_usao_press_releases(self, urls):
        """Scrape USAO press releases"""
        print("\n[SOURCE 1] USAO Press Releases")
        usao_count = 0
        
        for url in urls:
            try:
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                title = soup.find('h1')
                title = title.text.strip() if title else "Unknown"
                
                body = soup.find('article') or soup.find('main')
                details = body.get_text() if body else ""
                
                if self.is_relevant(title, details):
                    location = self.extract_location_federal(details)
                    
                    case = {
                        'title': title,
                        'location': location,
                        'details': details[:1000],
                        'source': 'USAO',
                        'url': url,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    self.cases.append(case)
                    usao_count += 1
                
                time.sleep(0.5)
            except Exception as e:
                print(f"  Error: {url[:50]}: {str(e)[:30]}")
        
        print(f"  Scraped: {usao_count} relevant cases from USAO")
        return usao_count
    
    def scrape_state_ag_all(self):
        """Scrape all 50 states + territories"""
        print("\n[SOURCE 2] State Attorney General (50 States + 5 Territories)")
        ag_count = 0
        
        for state, url in STATE_AG_URLS.items():
            try:
                response = self.session.get(url, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                title = soup.find('h1') or soup.find('title')
                title = title.text.strip() if title else f"{state} AG News"
                
                body = soup.find('article') or soup.find('main')
                details = body.get_text() if body else ""
                
                if self.is_relevant(title, details):
                    case = {
                        'title': title,
                        'location': state,
                        'details': details[:1000],
                        'source': f'{state} AG',
                        'url': url,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    self.cases.append(case)
                    ag_count += 1
                    print(f"  ✓ {state}")
                else:
                    print(f"  - {state} (no relevant cases)")
                
                time.sleep(0.5)
            except Exception as e:
                print(f"  ✗ {state}: {str(e)[:30]}")
        
        print(f"  Scraped: {ag_count} relevant cases from State AGs")
        return ag_count
    
    def scrape_google_rss(self, queries):
        """Scrape Google News RSS feeds"""
        print("\n[SOURCE 3] Google News RSS Feeds")
        rss_count = 0
        
        for query in queries:
            try:
                rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                response = self.session.get(rss_url, timeout=10)
                soup = BeautifulSoup(response.content, 'xml')
                
                items = soup.find_all('item')[:5]
                
                for item in items:
                    title = item.find('title')
                    title = title.text if title else "Unknown"
                    
                    description = item.find('description')
                    details = description.text if description else ""
                    
                    if self.is_relevant(title, details):
                        location = self.extract_location_federal(details)
                        
                        case = {
                            'title': title,
                            'location': location,
                            'details': details[:1000],
                            'source': f'Google News ({query})',
                            'scraped_at': datetime.now().isoformat()
                        }
                        
                        self.cases.append(case)
                        rss_count += 1
                
                print(f"  ✓ '{query}'")
                time.sleep(0.5)
            except Exception as e:
                print(f"  ✗ '{query}': {str(e)[:30]}")
        
        print(f"  Scraped: {rss_count} relevant cases from Google News")
        return rss_count
    
    def run_full_pipeline(self, usao_urls=[], google_queries=['federal prosecutions', 'public official corruption']):
        """Run complete scraping pipeline from all sources"""
        print(f"\n{'='*70}")
        print("VeriScope Master Scraper - All Sources")
        print(f"{'='*70}")
        
        usao_count = self.scrape_usao_press_releases(usao_urls) if usao_urls else 0
        ag_count = self.scrape_state_ag_all()
        rss_count = self.scrape_google_rss(google_queries)
        
        print(f"\n{'='*70}")
        print("Results Summary")
        print(f"{'='*70}")
        print(f"USAO Cases: {usao_count}")
        print(f"State AG Cases: {ag_count}")
        print(f"Google News Cases: {rss_count}")
        print(f"Total Cases: {len(self.cases)}")
        print(f"{'='*70}\n")
        
        return self.cases
    
    def validate_cases(self):
        """Validate cases with VeriScope validators"""
        print("\n[VALIDATION] Running jurisdiction validator...")
        validator = CaseValidator()
        result = validator.validate(self.cases)
        
        print(f"  Valid: {result['valid']}")
        print(f"  Rejected: {result['invalid']}")
        
        return result['valid_cases']
    
    def save_to_json(self, filename='master_scraper_cases.json'):
        """Save all cases"""
        with open(filename, 'w') as f:
            json.dump(self.cases, f, indent=2)
        print(f"\nSaved {len(self.cases)} cases to {filename}")
    
    def get_stats(self):
        """Print statistics"""
        print(f"\n{'='*70}")
        print("Statistics")
        print(f"{'='*70}")
        
        by_source = {}
        by_location = {}
        
        for case in self.cases:
            source = case.get('source', 'Unknown')
            location = case.get('location', 'Unknown')
            
            by_source[source] = by_source.get(source, 0) + 1
            by_location[location] = by_location.get(location, 0) + 1
        
        print("\nBy Source:")
        for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
            print(f"  {source}: {count}")
        
        print("\nTop Locations:")
        for location, count in sorted(by_location.items(), key=lambda x: -x[1])[:10]:
            print(f"  {location}: {count}")

if __name__ == "__main__":
    scraper = MasterScraper()
    
    # Run with empty USAO URLs (add your URLs here)
    cases = scraper.run_full_pipeline(
        usao_urls=[],  # Add USAO URLs if available
        google_queries=['federal prosecutions', 'public official corruption', 'attorney general indictment']
    )
    
    # Validate
    valid_cases = scraper.validate_cases()
    
    # Save
    scraper.save_to_json('master_scraper_cases.json')
    scraper.get_stats()
    
    print(f"\nReady to upload {len(valid_cases)} valid cases to Supabase!")
