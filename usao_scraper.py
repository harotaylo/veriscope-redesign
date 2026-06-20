"""
VeriScope USAO Scraper with Location Extraction
Scrapes DOJ USAO press releases with proper federal district mapping
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

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

PUBLIC_OFFICIAL_KEYWORDS = [
    'judge', 'magistrate', 'senator', 'congressman', 'representative',
    'state senator', 'state representative', 'mayor', 'governor',
    'sheriff', 'police officer', 'district attorney', 'prosecutor',
    'federal agent', 'fbi agent', 'dea agent', 'atf agent',
    'city council', 'county commissioner', 'alderman', 'councilman'
]

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty plea', 'indicted', 'charged', 'sentenced',
    'bribery', 'extortion', 'fraud', 'corruption', 'embezzlement',
    'money laundering', 'wire fraud', 'mail fraud'
]

class USAOScraper:
    def __init__(self):
        self.cases = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_location(self, text):
        """Extract federal district from press release text"""
        if not text:
            return "Unknown"
        
        text_upper = text.upper()
        
        # Look for "U.S. Attorney for the District of..."
        match = re.search(
            r"U\.S\.\s+ATTORNEY(?:'S\s+OFFICE)?\s+(?:FOR\s+THE\s+)?(?:DISTRICT\s+OF\s+)?(?:THE\s+)?(.+?)(?:\.|,|ANNOUNCED|$)",
            text_upper
        )
        
        if match:
            district_text = match.group(1).strip()
            # Clean up the text
            district_text = re.sub(r'\s+', ' ', district_text)
            
            # Match against known districts
            for key, value in DISTRICT_MAP.items():
                if key in district_text:
                    return value
        
        # Fallback: look for state names
        states = [
            'CALIFORNIA', 'FLORIDA', 'GEORGIA', 'NEW YORK', 'TEXAS', 'PENNSYLVANIA',
            'ILLINOIS', 'OHIO', 'VIRGINIA', 'NORTH CAROLINA', 'TENNESSEE', 'LOUISIANA',
            'MICHIGAN', 'MINNESOTA', 'WISCONSIN', 'MASSACHUSETTS', 'NEW JERSEY',
            'COLORADO', 'WASHINGTON', 'ARIZONA', 'OKLAHOMA', 'OREGON', 'INDIANA',
            'MISSOURI', 'UTAH', 'NEVADA', 'NEW MEXICO', 'KANSAS', 'ARKANSAS',
            'IOWA', 'CONNECTICUT', 'KENTUCKY', 'ALABAMA', 'SOUTH CAROLINA',
            'MARYLAND', 'NEBRASKA', 'IDAHO', 'HAWAII', 'MAINE', 'VERMONT',
            'ALASKA', 'DELAWARE', 'DISTRICT OF COLUMBIA'
        ]
        
        for state in states:
            if state in text_upper:
                return state.title()
        
        return "Unknown"
    
    def is_relevant_case(self, title, details):
        """Check if case is about public official misconduct"""
        text = (title + " " + details).lower()
        
        has_official = any(kw in text for kw in PUBLIC_OFFICIAL_KEYWORDS)
        has_misconduct = any(kw in text for kw in MISCONDUCT_KEYWORDS)
        
        return has_official and has_misconduct
    
    def parse_case(self, item):
        """Convert press release to case object"""
        try:
            title = item.get('title', 'Unknown').strip()
            url = item.get('url', '')
            details = item.get('details', '')
            location = item.get('location', 'Unknown')
            
            return {
                'title': title,
                'location': location,
                'details': details,
                'url': url,
                'official_type': 'Public Official',
                'position_title': 'Unknown',
                'case_status': 'Unknown',
                'scraped_at': datetime.now().isoformat()
            }
        except Exception as e:
            log.error(f"Error parsing case: {e}")
            return None
    
    def scrape_press_release(self, url):
        """Scrape a single DOJ press release"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('h1') or soup.find('title')
            title = title_tag.text.strip() if title_tag else "Unknown"
            
            # Extract body text
            body = soup.find('article') or soup.find('main') or soup.find('body')
            details = body.get_text() if body else ""
            
            # Extract location
            location = self.extract_location(details)
            
            # Check if relevant
            if not self.is_relevant_case(title, details):
                return None
            
            case_data = {
                'title': title,
                'details': details[:1000],
                'location': location,
                'url': url
            }
            
            case = self.parse_case(case_data)
            return case
        
        except Exception as e:
            log.error(f"Error scraping {url}: {e}")
            return None
    
    def scrape_from_list(self, urls):
        """Scrape multiple press release URLs"""
        log.info(f"Starting to scrape {len(urls)} URLs")
        
        for i, url in enumerate(urls, 1):
            case = self.scrape_press_release(url)
            if case:
                self.cases.append(case)
                log.info(f"[{i}/{len(urls)}] {case['title'][:50]} -> {case['location']}")
            else:
                log.info(f"[{i}/{len(urls)}] Skipped (not relevant)")
            
            time.sleep(0.5)  # Be respectful to servers
        
        log.info(f"Scraped {len(self.cases)} relevant cases")
        return self.cases
    
    def save_to_json(self, filename='usao_cases.json'):
        """Save cases to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.cases, f, indent=2)
        log.info(f"Saved {len(self.cases)} cases to {filename}")
    
    def get_location_stats(self):
        """Get statistics on location extraction"""
        unknown_count = sum(1 for c in self.cases if c['location'] == 'Unknown')
        known_count = len(self.cases) - unknown_count
        
        print(f"\nLocation Extraction Stats:")
        print(f"  Total cases: {len(self.cases)}")
        print(f"  With location: {known_count} ({100*known_count//len(self.cases) if self.cases else 0}%)")
        print(f"  Unknown location: {unknown_count} ({100*unknown_count//len(self.cases) if self.cases else 0}%)")
        
        # Show location distribution
        locations = {}
        for case in self.cases:
            loc = case['location']
            locations[loc] = locations.get(loc, 0) + 1
        
        print(f"\n  Top locations:")
        for loc, count in sorted(locations.items(), key=lambda x: -x[1])[:10]:
            print(f"    {loc}: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape DOJ USAO press releases')
    parser.add_argument('--file', help='JSON file with URLs to scrape')
    parser.add_argument('--output', default='usao_cases.json', help='Output JSON file')
    args = parser.parse_args()
    
    scraper = USAOScraper()
    
    if args.file:
        with open(args.file, 'r') as f:
            urls = json.load(f)
        scraper.scrape_from_list(urls)
    else:
        log.info("No input file specified. Use --file to provide URLs.")
        log.info("Example: python usao_scraper.py --file urls.json --output cases.json")
    
    if scraper.cases:
        scraper.save_to_json(args.output)
        scraper.get_location_stats()
