#!/usr/bin/env python3
import json
import requests
import hashlib
import re
from datetime import datetime
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

STATE_CODES = {
    'CA': 'California', 'TX': 'Texas', 'FL': 'Florida', 'NY': 'New York',
    'PA': 'Pennsylvania', 'IL': 'Illinois', 'OH': 'Ohio', 'GA': 'Georgia',
    'NC': 'North Carolina', 'MI': 'Michigan', 'NJ': 'New Jersey',
    'VA': 'Virginia', 'WA': 'Washington', 'AZ': 'Arizona', 'MA': 'Massachusetts',
    'CO': 'Colorado', 'MN': 'Minnesota', 'TN': 'Tennessee', 'MO': 'Missouri',
    'MD': 'Maryland', 'WI': 'Wisconsin', 'IN': 'Indiana', 'LA': 'Louisiana',
    'SC': 'South Carolina', 'KY': 'Kentucky', 'OK': 'Oklahoma', 'AL': 'Alabama'
}

def get_position(text):
    text_lower = text.lower()
    # Check longer keywords first to avoid partial matches
    sorted_keywords = sorted(POSITIONS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in text_lower:
            return POSITIONS[keyword]
    # Try regex patterns as fallback
    patterns = [
        r'\bHon\.\s+', r'\bJudge\b', r'\bSheriff\b', r'\bDeputy\b',
        r'\bMarshal\b', r'\bConstable\b', r'\bChief\b', r'\bOfficer\b',
        r'\bProsecutor\b', r'\bAttorney\b', r'\bDirector\b'
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            match = re.search(pattern, text, re.IGNORECASE).group()
            for kw, pos in POSITIONS.items():
                if kw in match.lower():
                    return pos
    return 'Official'

def get_official_type(position):
    return POSITION_TYPE.get(position, 'Executive')

def get_status(text):
    text_lower = text.lower()

    # Check convicted first (highest priority)
    if 'convicted' in text_lower or 'guilty plea' in text_lower or 'guilty verdict' in text_lower:
        return 'Convicted'
    elif 'sentenced' in text_lower or 'imprisonment' in text_lower or 'prison' in text_lower:
        return 'Convicted'
    # Then acquitted
    elif 'acquitted' in text_lower or 'not guilty' in text_lower or 'found not guilty' in text_lower:
        return 'Acquitted'
    # Then dismissed
    elif 'dismissed' in text_lower or 'case dismissed' in text_lower or 'charges dismissed' in text_lower:
        return 'Dismissed'
    # Then indicted/charged
    elif 'indicted' in text_lower or 'grand jury' in text_lower or 'indictment' in text_lower:
        return 'Indicted'
    elif 'charged' in text_lower or 'arraigned' in text_lower or 'charges filed' in text_lower:
        return 'Indicted'
    # Default based on context
    else:
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

def scrape_google_scholar_state(state_code, state_name, max_pages=3):
    """Scrape Google Scholar for state-level court decisions."""
    print(f"\n  Scraping Google Scholar for {state_name}...")
    cases = []

    searches = [
        f'{state_name} judge convicted',
        f'{state_name} official indicted',
        f'{state_name} sheriff charged',
        f'{state_name} prosecutor misconduct',
        f'{state_name} court corruption'
    ]

    for search_term in searches:
        try:
            for page in range(max_pages):
                url = 'https://scholar.google.com/scholar'
                params = {
                    'q': search_term,
                    'start': page * 10,
                    'as_ylo': 2020
                }

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }

                resp = requests.get(url, params=params, headers=headers, timeout=15)

                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.content, 'html.parser')
                results = soup.find_all('div', {'class': 'gs_ri'})

                if not results:
                    break

                for result in results:
                    try:
                        title_elem = result.find('h3', {'class': 'gs_rt'})
                        if not title_elem:
                            continue

                        title = title_elem.get_text().strip()
                        if len(title) < 10:
                            continue

                        snippet_elem = result.find('div', {'class': 'gs_rs'})
                        snippet = snippet_elem.get_text() if snippet_elem else ''

                        link_elem = result.find('a')
                        source_url = link_elem.get('href') if link_elem else ''

                        position = get_position(title + ' ' + snippet)
                        status = get_status(title + ' ' + snippet)
                        official_type = get_official_type(position)

                        case = {
                            'full_name': get_name(title),
                            'title': title[:150],
                            'position_title': position,
                            'official_type': official_type,
                            'location': state_code,
                            'level': 'State',
                            'category': 'Misconduct',
                            'abuse_of_power_type': 'Misconduct',
                            'case_status': status,
                            'details': snippet[:1000],
                            'source_url': source_url,
                            'source_type': 'court_record',
                            'source_date': str(datetime.now().date()),
                            'publication_status': 'draft',
                            'verified_by': 'state_courts_scraper',
                            'verified_at': datetime.now().isoformat(),
                            'fingerprint': hashlib.md5((title + source_url).encode()).hexdigest()[:16]
                        }

                        cases.append(case)

                    except:
                        continue

        except Exception as e:
            pass

    return cases

def scrape_state_courts():
    print("\n" + "="*70)
    print("VeriScope - State Courts Scraper")
    print("="*70)

    all_cases = []

    for state_code, state_name in list(STATE_CODES.items())[:5]:
        try:
            state_cases = scrape_google_scholar_state(state_code, state_name)
            all_cases.extend(state_cases)
            print(f"    Found: {len(state_cases)} cases")
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

    with open('state_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved: state_cases.json")

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
