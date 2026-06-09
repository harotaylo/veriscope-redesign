#!/usr/bin/env python3
import json
import requests
import hashlib
import re
from datetime import datetime
import time

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

# USAO district code → State name
USAO_TO_STATE = {
    'usao-al': 'Alabama', 'usao-ndal': 'Alabama', 'usao-mdal': 'Alabama', 'usao-sdal': 'Alabama',
    'usao-ak': 'Alaska',
    'usao-az': 'Arizona',
    'usao-ar': 'Arkansas', 'usao-edar': 'Arkansas', 'usao-wdar': 'Arkansas',
    'usao-ca': 'California', 'usao-cdca': 'California', 'usao-edca': 'California',
    'usao-ndca': 'California', 'usao-sdca': 'California',
    'usao-co': 'Colorado',
    'usao-ct': 'Connecticut',
    'usao-de': 'Delaware',
    'usao-dc': 'District of Columbia',
    'usao-fl': 'Florida', 'usao-ndfl': 'Florida', 'usao-mdfl': 'Florida', 'usao-sdfl': 'Florida',
    'usao-ga': 'Georgia', 'usao-ndga': 'Georgia', 'usao-mdga': 'Georgia', 'usao-sdga': 'Georgia',
    'usao-hi': 'Hawaii',
    'usao-id': 'Idaho',
    'usao-il': 'Illinois', 'usao-ndil': 'Illinois', 'usao-cdil': 'Illinois', 'usao-sdil': 'Illinois',
    'usao-in': 'Indiana', 'usao-ndin': 'Indiana', 'usao-sdin': 'Indiana',
    'usao-ia': 'Iowa', 'usao-ndia': 'Iowa', 'usao-sdia': 'Iowa',
    'usao-ks': 'Kansas',
    'usao-ky': 'Kentucky', 'usao-edky': 'Kentucky', 'usao-wdky': 'Kentucky',
    'usao-la': 'Louisiana', 'usao-edla': 'Louisiana', 'usao-mdla': 'Louisiana', 'usao-wdla': 'Louisiana',
    'usao-me': 'Maine',
    'usao-md': 'Maryland',
    'usao-ma': 'Massachusetts',
    'usao-mi': 'Michigan', 'usao-edmi': 'Michigan', 'usao-wdmi': 'Michigan',
    'usao-mn': 'Minnesota',
    'usao-ms': 'Mississippi', 'usao-ndms': 'Mississippi', 'usao-sdms': 'Mississippi',
    'usao-mo': 'Missouri', 'usao-edmo': 'Missouri', 'usao-wdmo': 'Missouri',
    'usao-mt': 'Montana',
    'usao-ne': 'Nebraska',
    'usao-nv': 'Nevada',
    'usao-nh': 'New Hampshire',
    'usao-nj': 'New Jersey',
    'usao-nm': 'New Mexico',
    'usao-ny': 'New York', 'usao-edny': 'New York', 'usao-ndny': 'New York',
    'usao-sdny': 'New York', 'usao-wdny': 'New York',
    'usao-nc': 'North Carolina', 'usao-ednc': 'North Carolina', 'usao-mdnc': 'North Carolina', 'usao-wdnc': 'North Carolina',
    'usao-nd': 'North Dakota',
    'usao-oh': 'Ohio', 'usao-ndoh': 'Ohio', 'usao-sdoh': 'Ohio',
    'usao-ok': 'Oklahoma', 'usao-edok': 'Oklahoma', 'usao-ndok': 'Oklahoma', 'usao-wdok': 'Oklahoma',
    'usao-or': 'Oregon',
    'usao-pa': 'Pennsylvania', 'usao-edpa': 'Pennsylvania', 'usao-mdpa': 'Pennsylvania', 'usao-wdpa': 'Pennsylvania',
    'usao-ri': 'Rhode Island',
    'usao-sc': 'South Carolina',
    'usao-sd': 'South Dakota',
    'usao-tn': 'Tennessee', 'usao-edtn': 'Tennessee', 'usao-mdtn': 'Tennessee', 'usao-wdtn': 'Tennessee',
    'usao-tx': 'Texas', 'usao-edtx': 'Texas', 'usao-ndtx': 'Texas', 'usao-sdtx': 'Texas', 'usao-wdtx': 'Texas',
    'usao-ut': 'Utah',
    'usao-vt': 'Vermont',
    'usao-va': 'Virginia', 'usao-edva': 'Virginia', 'usao-wdva': 'Virginia',
    'usao-wa': 'Washington', 'usao-edwa': 'Washington', 'usao-wdwa': 'Washington',
    'usao-wv': 'West Virginia', 'usao-ndwv': 'West Virginia', 'usao-sdwv': 'West Virginia',
    'usao-wi': 'Wisconsin', 'usao-edwi': 'Wisconsin', 'usao-wdwi': 'Wisconsin',
    'usao-wy': 'Wyoming',
    'usao-pr': 'Puerto Rico',
    'usao-vi': 'Virgin Islands',
    'usao-guam': 'Guam',
}

FEDERAL_OFFICIALS = [
    'president', 'vice president', 'cabinet secretary', 'congressman', 'congresswoman',
    'federal judge', 'federal prosecutor', 'u.s. attorney', 'assistant u.s. attorney',
    'federal agent', 'fbi agent', 'dea agent', 'senator', 'representative'
]

STATE_OFFICIALS = [
    'lieutenant governor', 'state senator', 'state representative', 'state judge',
    'state attorney general', 'state treasurer', 'state auditor', 'state inspector general',
    'state trooper', 'state police officer', 'state corrections officer', 'governor'
]

COUNTY_OFFICIALS = [
    'county commissioner', 'county judge', 'county clerk', 'district attorney',
    'county attorney', 'assistant district attorney', 'county auditor', 'county treasurer',
    'county assessor', 'county sheriff', 'deputy sheriff', 'constable'
]

CITY_OFFICIALS = [
    'city manager', 'town manager', 'city council member', 'alderman', 'alderwoman',
    'city attorney', 'city auditor', 'city comptroller', 'police chief', 'deputy police chief',
    'fire chief', 'fire commissioner', 'mayor', 'city council'
]

ALL_OFFICIALS = FEDERAL_OFFICIALS + STATE_OFFICIALS + COUNTY_OFFICIALS + CITY_OFFICIALS

EXCLUDE_KEYWORDS = [
    'gang member', 'drug dealer', 'felon', 'suspect', 'businessman',
    'activist', 'citizen', 'resident', 'private citizen',
    'business owner', 'contractor', 'worker', 'terrorist',
    'al-qaeda', 'isis', 'jihad', 'extremist', 'militia member',
    'inmate', 'prisoner', 'convict', 'fugitive', 'smuggler',
    'trafficker', 'hacker', 'fraudster', 'scammer'
]

VICTIM_TITLE_KEYWORDS = [
    'plotting to murder', 'plot to kill', 'plot to murder',
    'threatening', 'threatens', 'threatened to kill',
    'attack on', 'assault on', 'murder of', 'killing of',
    'against the judge', 'targeting judge', 'targeting officer',
    'man facing', 'woman facing', 'men facing', 'person facing',
    'attempted murder of', 'conspiracy to kill',
    'solicitation to murder', 'soliciting murder',
    'shooting at', 'fired at', 'shot at',
    'threats against', 'threat against',
    'charged with killing', 'charged with murdering',
    'indicted for killing', 'indicted for murdering',
    'for killing', 'for murdering', 'for shooting'
]

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty', 'indicted', 'charged', 'corruption', 'bribery',
    'fraud', 'removed', 'suspended', 'sentenced', 'plea', 'conspiracy',
    'embezzle', 'theft', 'abuse', 'illegal', 'misconduct', 'crime', 'criminal'
]

MONTHS = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8,
    'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

def get_location_from_url(url):
    """Extract state from DOJ source URL via USAO district code"""
    if not url:
        return 'Unknown'
    url_lower = url.lower()
    # Match longest key first to avoid partial matches
    for code in sorted(USAO_TO_STATE.keys(), key=len, reverse=True):
        if code in url_lower:
            return USAO_TO_STATE[code]
    # OPA = main DOJ office = Federal
    if '/opa/' in url_lower:
        return 'Federal'
    return 'Unknown'

def extract_date(text):
    if not text:
        return None
    text = text.replace('\n', ' ')

    match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})', text, re.IGNORECASE)
    if match:
        month = MONTHS.get(match.group(1).lower(), 1)
        try:
            return f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(2)):02d}"
        except:
            pass

    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if match:
        m, d, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100:
            return f"{y:04d}-{m:02d}-{d:02d}"

    match = re.search(r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', text, re.IGNORECASE)
    if match:
        month = MONTHS.get(match.group(2).lower(), 1)
        try:
            return f"{int(match.group(3)):04d}-{month:02d}-{int(match.group(1)):02d}"
        except:
            pass

    match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if match:
        return f"{match.group(1)}-{match.group(2):0>2}-{match.group(3):0>2}"

    return None

def get_level(text):
    t = text.lower()
    if any(kw in t for kw in FEDERAL_OFFICIALS): return 'Federal'
    if any(kw in t for kw in STATE_OFFICIALS): return 'State'
    if any(kw in t for kw in COUNTY_OFFICIALS): return 'County'
    if any(kw in t for kw in CITY_OFFICIALS): return 'City'
    return None

def is_official(title, body):
    title_lower = title.lower()
    combined = f"{title} {body}".lower()
    if not any(kw in combined for kw in ALL_OFFICIALS): return False
    if any(kw in title_lower for kw in VICTIM_TITLE_KEYWORDS): return False
    if any(kw in combined for kw in EXCLUDE_KEYWORDS): return False
    if not any(kw in combined for kw in MISCONDUCT_KEYWORDS): return False
    return True

def get_position(text):
    t = text.lower()
    if 'vice president' in t: return 'Vice President'
    if 'president' in t and 'vice' not in t: return 'President'
    if 'cabinet' in t: return 'Cabinet Secretary'
    if 'federal judge' in t: return 'Federal Judge'
    if 'u.s. attorney' in t or 'us attorney' in t: return 'U.S. Attorney'
    if 'federal prosecutor' in t: return 'Federal Prosecutor'
    if 'fbi agent' in t: return 'FBI Agent'
    if 'dea agent' in t: return 'DEA Agent'
    if 'congressman' in t or 'congresswoman' in t: return 'Congressman'
    if 'senator' in t: return 'Senator'
    if 'representative' in t: return 'Representative'
    if 'lieutenant governor' in t: return 'Lieutenant Governor'
    if 'governor' in t: return 'Governor'
    if 'state senator' in t: return 'State Senator'
    if 'state representative' in t: return 'State Representative'
    if 'state judge' in t: return 'State Judge'
    if 'state attorney general' in t: return 'State Attorney General'
    if 'state treasurer' in t: return 'State Treasurer'
    if 'state auditor' in t: return 'State Auditor'
    if 'state trooper' in t or 'state police' in t: return 'State Police Officer'
    if 'county commissioner' in t: return 'County Commissioner'
    if 'county judge' in t: return 'County Judge'
    if 'county clerk' in t: return 'County Clerk'
    if 'district attorney' in t: return 'District Attorney'
    if 'county attorney' in t: return 'County Attorney'
    if 'county auditor' in t: return 'County Auditor'
    if 'county treasurer' in t: return 'County Treasurer'
    if 'deputy sheriff' in t: return 'Deputy Sheriff'
    if 'county sheriff' in t or 'sheriff' in t: return 'Sheriff'
    if 'constable' in t: return 'Constable'
    if 'city manager' in t or 'town manager' in t: return 'City Manager'
    if 'city council' in t: return 'City Council Member'
    if 'alderman' in t or 'alderwoman' in t: return 'Alderman'
    if 'city attorney' in t: return 'City Attorney'
    if 'city auditor' in t: return 'City Auditor'
    if 'city comptroller' in t: return 'City Comptroller'
    if 'deputy police chief' in t: return 'Deputy Police Chief'
    if 'police chief' in t: return 'Police Chief'
    if 'fire chief' in t or 'fire commissioner' in t: return 'Fire Chief'
    if 'mayor' in t: return 'Mayor'
    if 'police' in t or 'officer' in t: return 'Police Officer'
    return 'Public Official'

def get_official_type(text):
    t = text.lower()
    if 'judge' in t: return 'Judicial'
    if any(x in t for x in ['police', 'sheriff', 'officer', 'detective', 'agent']): return 'Law Enforcement'
    if any(x in t for x in ['senator', 'representative', 'congressman', 'council']): return 'Legislative'
    return 'Executive'

def get_status(text):
    t = text.lower()
    if 'convicted' in t or 'guilty plea' in t or 'guilty' in t: return 'Convicted'
    if 'indicted' in t or 'grand jury' in t: return 'Indicted'
    if 'charged' in t and 'convicted' not in t: return 'Indicted'
    if 'dismissed' in t: return 'Dismissed'
    if 'acquitted' in t: return 'Acquitted'
    return 'Convicted'

def get_name(title):
    title = re.sub(r'^(Former|Retired|Ex-)\s+', '', title, flags=re.IGNORECASE)
    if ' - ' in title:
        name = title.split(' - ')[0].strip()
        if 3 < len(name) < 150:
            return name[:100]
    for verb in ['Convicted', 'Charged', 'Indicted', 'Sentenced', 'Plead']:
        if verb in title:
            return title.split(verb)[0].strip()[:100]
    return 'Unknown Official'

def scrape_doj(term):
    cases = []
    try:
        resp = requests.get(
            'https://www.justice.gov/api/v1/press_releases.json',
            params={'limit': 100, 'title': term},
            timeout=10
        )
        if resp.status_code != 200:
            return cases

        for r in resp.json().get('results', []):
            try:
                title = r.get('title', '').strip()
                body = r.get('body', '').strip()
                url = r.get('url', '')
                if not title or not body:
                    continue
                if not is_official(title, body):
                    continue

                combined = f"{title} {body}"
                level = get_level(combined)
                if not level:
                    continue

                # Extract state from source URL
                location = get_location_from_url(url)

                cases.append({
                    'full_name': get_name(title),
                    'title': title[:150],
                    'position_title': get_position(combined),
                    'official_type': get_official_type(combined),
                    'location': location,
                    'level': level,
                    'category': 'Corruption',
                    'abuse_of_power_type': 'Corruption',
                    'case_status': get_status(combined),
                    'date_charged': extract_date(combined),
                    'details': body[:1000],
                    'source_url': url,
                    'source_type': 'court_record',
                    'source_date': str(datetime.now().date()),
                    'publication_status': 'draft',
                    'verified_by': 'comprehensive_scraper',
                    'verified_at': datetime.now().isoformat(),
                    'fingerprint': hashlib.md5(f"{title}_{url}".encode()).hexdigest()
                })
            except:
                continue
    except Exception as e:
        print(f"  Error: {str(e)[:60]}")
    return cases

def scrape_all():
    print("\n" + "="*70)
    print("VERISCOPE SCRAPER - STRICT VALIDATION + DATE + LOCATION")
    print("="*70 + "\n")

    search_terms = [
        # Federal
        'federal judge convicted', 'federal judge indicted',
        'u.s. attorney charged', 'u.s. attorney convicted',
        'senator guilty', 'senator convicted', 'senator indicted',
        'congressman convicted', 'congressman indicted', 'congressman guilty',
        'representative convicted', 'representative indicted',
        'federal prosecutor indicted', 'fbi agent convicted', 'fbi agent indicted',
        'cabinet secretary convicted',
        # State
        'state judge convicted', 'state judge indicted',
        'state attorney general charged',
        'state senator guilty', 'state representative convicted',
        'governor convicted', 'governor indicted', 'governor guilty',
        'state treasurer convicted', 'state auditor indicted',
        # County
        'county commissioner convicted', 'county judge charged',
        'district attorney guilty', 'district attorney convicted',
        'county sheriff indicted', 'sheriff convicted', 'sheriff indicted',
        'county attorney charged', 'deputy sheriff convicted',
        # City
        'mayor convicted', 'mayor indicted',
        'city council guilty', 'city council convicted',
        'police chief indicted', 'police chief convicted',
        'fire chief convicted', 'city attorney charged',
        'alderman guilty', 'city manager indicted'
    ]

    all_cases = []
    for term in search_terms:
        print(f"  {term:45}", end='', flush=True)
        cases = scrape_doj(term)
        all_cases.extend(cases)
        print(f" Found: {len(cases)}")
        time.sleep(0.5)

    return all_cases

def upload(cases):
    if not cases:
        print("\nNo cases to upload")
        return 0

    # Deduplicate by fingerprint before uploading
    seen = {}
    for c in cases:
        seen[c['fingerprint']] = c
    cases = list(seen.values())

    print(f"\n" + "="*70)
    print(f"Total unique cases: {len(cases)}")

    statuses, positions, levels, locations = {}, {}, {}, {}
    dates_found = 0
    for c in cases:
        statuses[c['case_status']] = statuses.get(c['case_status'], 0) + 1
        positions[c['position_title']] = positions.get(c['position_title'], 0) + 1
        levels[c['level']] = levels.get(c['level'], 0) + 1
        locations[c['location']] = locations.get(c['location'], 0) + 1
        if c.get('date_charged'):
            dates_found += 1

    print("\nBy Status:")
    for k, v in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k}: {v}")

    print("\nTop Positions:")
    for k, v in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {k}: {v}")

    print("\nBy Level:")
    for k, v in sorted(levels.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k}: {v}")

    print("\nTop Locations:")
    for k, v in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {k}: {v}")

    print(f"\nDates extracted: {dates_found}/{len(cases)}")

    with open('cases_output.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"Saved: cases_output.json")

    print(f"\n" + "="*70)
    print("Uploading to Supabase (upsert - no duplicate errors)...")

    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        uploaded = 0
        for i in range(0, len(cases), 50):
            chunk = cases[i:i + 50]
            try:
                supabase.table('cases').upsert(chunk, on_conflict='fingerprint').execute()
                uploaded += len(chunk)
                print(f"  [+] {uploaded}/{len(cases)}")
            except Exception as e:
                print(f"  Error: {str(e)[:80]}")

        return uploaded

    except ImportError:
        print("Supabase not available - saved to JSON only")
        return 0

if __name__ == '__main__':
    cases = scrape_all()
    uploaded = upload(cases)

    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} cases upserted")
    print("="*70 + "\n")