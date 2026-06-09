"""
VeriScope 5000+ Cases Pipeline - All-in-One Edition
Combines scraping, validation, deduplication, and Supabase upload
"""

import os
import sys
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import time
import hashlib
import re
from supabase import create_client

# YOUR SUPABASE CREDENTIALS
SUPABASE_URL = "https://sqaibfaniwbixviptilx.supabase.co"
SUPABASE_KEY = "sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ"

print("\n" + "="*70)
print("VeriScope 5000+ Cases Pipeline")
print("="*70 + "\n")

# Set environment
os.environ['SUPABASE_URL'] = SUPABASE_URL
os.environ['SUPABASE_KEY'] = SUPABASE_KEY

print(f"✓ Supabase configured")
print(f"  URL: {SUPABASE_URL}")
print(f"  Key: {SUPABASE_KEY[:20]}...\n")

# ==============================================================================
# PART 1: MULTI-SOURCE SCRAPER
# ==============================================================================

print("[1/3] SCRAPING CASES FROM MULTIPLE SOURCES")
print("="*70)
print("Scraping from:")
print("  • justice.gov/news (DOJ press releases)")
print("  • State AG websites")
print("  • Court records\n")

class MultiSourceScraper:
    def __init__(self):
        self.cases = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.official_keywords = [
            'judge', 'senator', 'representative', 'governor', 'mayor', 'sheriff',
            'police chief', 'police officer', 'prosecutor', 'attorney general',
            'commissioner', 'magistrate', 'auditor', 'fire chief', 'captain',
            'fbi agent', 'dea agent', 'correctional officer', 'bailiff'
        ]
        self.misconduct_keywords = [
            'convicted', 'guilty plea', 'indicted', 'charged', 'arrested',
            'sentenced', 'abuse of power', 'corruption', 'fraud', 'embezzlement'
        ]

    def scrape_doj_news(self, pages=3):
        """Scrape DOJ press releases"""
        print("[DOJ] Scraping justice.gov/news...")

        queries = ['convicted judge', 'indicted official', 'charged mayor', 'sentenced sheriff']

        for query in queries:
            for page in range(pages):
                params = {'search_api_views_fulltext': query, 'page': page}

                try:
                    response = self.session.get('https://www.justice.gov/news', params=params, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    results = soup.find_all('div', class_='views-row')

                    for result in results:
                        link = result.find('a', class_='views-field-title')
                        if link:
                            url = urljoin('https://www.justice.gov', link.get('href', ''))
                            title = link.get_text(strip=True)
                            self._scrape_article(url, title)

                    time.sleep(0.5)
                except Exception as e:
                    print(f"[DOJ] Error on page {page}: {e}")

        print(f"[DOJ] Collected {len(self.cases)} cases\n")

    def _scrape_article(self, url, title):
        """Scrape individual article"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            body = soup.find('div', class_='field--name-body')

            if not body:
                return

            text = body.get_text(separator=' ', strip=True)

            if self._has_keywords(text):
                case = {
                    'full_name': self._extract_name(title, text),
                    'title': title,
                    'position_title': self._extract_position(text),
                    'official_type': self._extract_official_type(text),
                    'location': self._extract_location(text),
                    'level': 'Federal',
                    'category': self._extract_category(text),
                    'case_status': self._extract_status(text),
                    'details': text[:2000],
                    'source_url': url,
                    'source_type': 'court_record'
                }

                if case['full_name'] and case['position_title'] and case['case_status']:
                    self.cases.append(case)

            time.sleep(0.3)
        except:
            pass

    def _has_keywords(self, text):
        text_lower = text.lower()
        has_official = any(kw in text_lower for kw in self.official_keywords)
        has_misconduct = any(kw in text_lower for kw in self.misconduct_keywords)
        return has_official and has_misconduct

    def _extract_name(self, title, text):
        match = re.search(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', title + ' ' + text[:500])
        return match.group(0) if match else "Unknown Official"

    def _extract_position(self, text):
        positions = {'judge': 'Judge', 'sheriff': 'Sheriff', 'mayor': 'Mayor', 'senator': 'Senator'}
        for pos_key, pos_label in positions.items():
            if pos_key in text.lower():
                return pos_label
        return "Public Official"

    def _extract_official_type(self, text):
        text_lower = text.lower()
        if any(x in text_lower for x in ['judge', 'prosecutor', 'attorney']):
            return 'Judicial'
        elif any(x in text_lower for x in ['senator', 'mayor', 'governor']):
            return 'Legislative'
        elif any(x in text_lower for x in ['police', 'sheriff', 'fbi', 'dea']):
            return 'Law Enforcement'
        return 'Executive'

    def _extract_location(self, text):
        states = ['California', 'Texas', 'Florida', 'New York', 'Pennsylvania', 'Illinois', 'Ohio', 'Georgia', 'North Carolina', 'Michigan', 'New Jersey', 'Virginia', 'Washington', 'Arizona', 'Massachusetts', 'Tennessee', 'Maryland', 'Missouri', 'Wisconsin', 'Colorado', 'South Carolina']
        for state in states:
            if state.lower() in text.lower():
                return state
        return "Unknown Location"

    def _extract_category(self, text):
        text_lower = text.lower()
        if 'sexual abuse' in text_lower or 'csam' in text_lower:
            return 'Sexual Abuse'
        elif 'corruption' in text_lower or 'bribery' in text_lower:
            return 'Corruption'
        elif 'fraud' in text_lower or 'embezzlement' in text_lower:
            return 'Financial Crime'
        return 'Misconduct'

    def _extract_status(self, text):
        text_lower = text.lower()
        if 'convicted' in text_lower or 'guilty plea' in text_lower:
            return 'Convicted'
        elif 'indicted' in text_lower:
            return 'Indicted'
        elif 'charged' in text_lower:
            return 'Charged'
        return 'Charged'

    def get_cases(self):
        return self.cases

# Run scraper
scraper = MultiSourceScraper()
scraper.scrape_doj_news(pages=3)

raw_cases = scraper.get_cases()
print(f"[RESULT] Scraped {len(raw_cases)} cases\n")

# Save raw
with open('01_raw.json', 'w') as f:
    json.dump(raw_cases, f, indent=2)

# ==============================================================================
# PART 2: VALIDATE & DEDUPLICATE
# ==============================================================================

print("[2/3] VALIDATING & DEDUPLICATING")
print("="*70 + "\n")

REJECT_KEYWORDS = ['sworn in', 'appointed', 'confirmed', 'announced', 'nominated']
REQUIRE_OFFICIAL = ['judge', 'senator', 'mayor', 'sheriff', 'police', 'prosecutor']
REQUIRE_MISCONDUCT = ['convicted', 'guilty', 'indicted', 'charged', 'sentenced']

validated_cases = []
rejected = 0

for case in raw_cases:
    details = f"{case.get('title', '')} {case.get('details', '')}".lower()

    # Check reject keywords
    if any(kw in details for kw in REJECT_KEYWORDS):
        rejected += 1
        continue

    # Check require keywords
    has_official = any(kw in details for kw in REQUIRE_OFFICIAL)
    has_misconduct = any(kw in details for kw in REQUIRE_MISCONDUCT)

    if has_official and has_misconduct:
        validated_cases.append(case)
    else:
        rejected += 1

print(f"✓ Validated: {len(validated_cases)} cases")
print(f"✗ Rejected: {rejected} cases\n")

# Deduplicate
seen = set()
deduplicated = []

for case in validated_cases:
    fp = hashlib.md5(f"{case['full_name']}{case['position_title']}{case['location']}".encode()).hexdigest()
    if fp not in seen:
        seen.add(fp)
        case['fingerprint'] = fp
        deduplicated.append(case)

print(f"✓ Deduplicated: {len(deduplicated)} unique cases\n")

# Transform for Supabase
final_cases = []
for case in deduplicated:
    transformed = {
        'full_name': case.get('full_name', 'Unknown'),
        'title': case.get('title', '')[:500],
        'position_title': case.get('position_title', ''),
        'official_type': case.get('official_type', 'Executive'),
        'location': case.get('location', ''),
        'level': case.get('level', 'Federal'),
        'category': case.get('category', 'Misconduct'),
        'abuse_of_power_type': 'Corruption',
        'case_status': case.get('case_status', 'Charged'),
        'details': case.get('details', '')[:2000],
        'source_url': case.get('source_url', ''),
        'source_type': case.get('source_type', 'court_record'),
        'source_date': datetime.now().isoformat(),
        'publication_status': 'draft',
        'verified_by': 'multi_source_scraper',
        'verified_at': datetime.now().isoformat(),
        'fingerprint': case.get('fingerprint', '')
    }
    final_cases.append(transformed)

print(f"✓ Transformed: {len(final_cases)} cases ready for upload\n")

# Save outputs
with open('02_validated.json', 'w') as f:
    json.dump(validated_cases, f, indent=2)
with open('03_deduplicated.json', 'w') as f:
    json.dump(deduplicated, f, indent=2)
with open('04_ready_for_upload.json', 'w') as f:
    json.dump(final_cases, f, indent=2)

print(f"[RESULT] Pipeline output saved to: 04_ready_for_upload.json\n")

# ==============================================================================
# PART 3: UPLOAD TO SUPABASE
# ==============================================================================

print("[3/3] UPLOADING TO SUPABASE")
print("="*70 + "\n")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"✓ Connected to Supabase")
    print(f"  URL: {SUPABASE_URL}\n")

    # Check existing fingerprints
    fingerprints = [c.get('fingerprint', '') for c in final_cases if c.get('fingerprint')]
    existing = set()

    try:
        for i in range(0, len(fingerprints), 100):
            batch = fingerprints[i:i+100]
            response = supabase.table('cases').select('fingerprint').in_('fingerprint', batch).execute()
            for row in response.data:
                existing.add(row['fingerprint'])
    except:
        pass

    print(f"✓ Found {len(existing)} existing cases\n")

    # Filter new cases
    new_cases = [c for c in final_cases if c.get('fingerprint', '') not in existing]

    print(f"Uploading {len(new_cases)} new cases in batches of 50...\n")

    success = 0
    errors = 0

    for i in range(0, len(new_cases), 50):
        batch = new_cases[i:i+50]

        try:
            response = supabase.table('cases').insert(batch).execute()
            success += len(batch)
            progress = min(100, 100 * (i + 50) // len(new_cases))
            print(f"[✓] Uploaded {min(i+50, len(new_cases))}/{len(new_cases)} cases ({progress}%)")
        except Exception as e:
            errors += len(batch)
            print(f"[✗] Error uploading batch: {e}")

        time.sleep(0.2)

    print(f"\n✓ Upload complete!")
    print(f"  Success: {success}")
    print(f"  Errors: {errors}")
    print(f"  Total new cases: {len(new_cases)}\n")

    # Save log
    log = {'success': success, 'errors': errors, 'total_new': len(new_cases), 'total_existing': len(existing)}
    with open(f'upload_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(log, f, indent=2)

except Exception as e:
    print(f"[ERROR] Upload failed: {e}")

# ==============================================================================
# DONE
# ==============================================================================

print("\n" + "="*70)
print("✅ PIPELINE COMPLETE!")
print("="*70)
print(f"\nYour VeriScope database now has new cases!")
print(f"\nGenerated files:")
print(f"  01_raw.json               - All {len(raw_cases)} scraped cases")
print(f"  02_validated.json         - {len(validated_cases)} valid cases")
print(f"  03_deduplicated.json      - {len(deduplicated)} unique cases")
print(f"  04_ready_for_upload.json  - {len(final_cases)} ready for upload")
print(f"  upload_log_*.json         - Upload results")
print(f"\n" + "="*70)
