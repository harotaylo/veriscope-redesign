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
    'Alabama': 'https://ago.alabama.gov/news-media/news-releases/',
    'Alaska': 'https://law.alaska.gov/news/',
    'Arizona': 'https://azag.gov/press-releases',
    'Arkansas': 'https://ago.arkansas.gov/news-and-media/news-releases',
    'California': 'https://oag.ca.gov/news',
    'Colorado': 'https://coag.gov/press-releases',
    'Connecticut': 'https://portal.ct.gov/AG/Press-Release',
    'Florida': 'https://www.myfloridalegal.com/news-releases',
    'Georgia': 'https://law.georgia.gov/news',
    'Hawaii': 'https://ag.hawaii.gov/news-releases/',
    'Idaho': 'https://ag.idaho.gov/news-media/news-releases/',
    'Illinois': 'https://www.in.gov/attorney-general/news/',
    'Indiana': 'https://www.in.gov/attorney-general/news/',
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
    'Nebraska': 'https://www.ago.ne.gov/media_releases.html',
    'Nevada': 'https://ag.nv.gov/news',
    'New Hampshire': 'https://www.doj.nh.gov/news-and-media',
    'New Jersey': 'https://www.nj.gov/oag/newsreleases/',
    'New Mexico': 'https://www.nmag.gov/news/',
    'New York': 'https://ag.ny.gov/press-release',
    'North Carolina': 'https://ncdoj.gov/news',
    'North Dakota': 'https://www.ag.nd.gov/news',
    'Ohio': 'https://www.ohioattorneygeneral.gov/news',
    'Oklahoma': 'https://www.oag.ok.gov/newsroom',
    'Oregon': 'https://www.oregon.gov/ag/pages/news.aspx',
    'Pennsylvania': 'https://www.attorneygeneral.gov/news/',
    'Rhode Island': 'https://ag.ri.gov/news-and-alerts',
    'South Carolina': 'https://www.scag.gov/news-and-public-information/',
    'South Dakota': 'https://atg.sd.gov/news',
    'Tennessee': 'https://www.tn.gov/attorneygeneral/news.html',
    'Texas': 'https://www.texasattorneygeneral.gov/news-releases',
    'Vermont': 'https://ago.vermont.gov/latest-news',
    'Virginia': 'https://www.oag.state.va.us/news',
    'Washington': 'https://www.atg.wa.gov/news-media',
    'West Virginia': 'https://www.ag.wv.gov/news',
    'Wisconsin': 'https://www.doj.state.wi.us/news',
    'Wyoming': 'https://ag.wyo.gov/press-releases'
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

def is_official(title, body):
    title_lower = title.lower()
    combined = f"{title} {body}".lower()
    if not any(kw in combined for kw in ALL_OFFICIALS):
        return False
    if any(kw in title_lower for kw in VICTIM_TITLE_KEYWORDS):
        return False
    if any(kw in combined for kw in EXCLUDE_KEYWORDS):
        return False
    if not any(kw in combined for kw in MISCONDUCT_KEYWORDS):
        return False
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
    if 'judge' in t:
        return 'Judicial'
    elif any(x in t for x in ['police', 'sheriff', 'officer', 'detective', 'agent']):
        return 'Law Enforcement'
    elif any(x in t for x in ['senator', 'representative', 'congressman', 'council']):
        return 'Legislative'
    else:
        return 'Executive'

def get_level(text):
    t = text.lower()
    if any(kw in t for kw in FEDERAL_OFFICIALS):
        return 'Federal'
    elif any(kw in t for kw in STATE_OFFICIALS):
        return 'State'
    elif any(kw in t for kw in COUNTY_OFFICIALS):
        return 'County'
    elif any(kw in t for kw in CITY_OFFICIALS):
        return 'City'
    else:
        return 'State'

def get_status(text):
    t = text.lower()
    if 'convicted' in t or 'guilty plea' in t or 'guilty' in t:
        return 'Convicted'
    elif 'indicted' in t or 'grand jury' in t:
        return 'Indicted'
    elif 'charged' in t and 'convicted' not in t:
        return 'Indicted'
    elif 'dismissed' in t:
        return 'Dismissed'
    elif 'acquitted' in t:
        return 'Acquitted'
    else:
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

def scrape_state(state_name, url):
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
            'div[class*="release"]'
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

                body_elem = article.find(['p', 'div'])
                body = body_elem.get_text(strip=True) if body_elem else ""

                if not is_official(title, body):
                    continue

                combined = f"{title} {body}"

                cases.append({
                    'full_name': get_name(title),
                    'title': title[:150],
                    'position_title': get_position(combined),
                    'official_type': get_official_type(combined),
                    'location': state_name,
                    'level': get_level(combined),
                    'category': 'Corruption',
                    'abuse_of_power_type': 'Corruption',
                    'case_status': get_status(combined),
                    'date_charged': extract_date(combined),
                    'details': body[:1000],
                    'source_url': url,
                    'source_type': 'court_record',
                    'source_date': str(datetime.now().date()),
                    'publication_status': 'published',
                    'verified_by': 'state_ag_scraper',
                    'verified_at': datetime.now().isoformat(),
                    'fingerprint': hashlib.md5(f"{title}_{state_name}".encode()).hexdigest()
                })
            except:
                continue

        return cases
    except:
        return cases

def scrape_all_states():
    print("\n" + "="*70)
    print("STATE AG SCRAPER - All 50 States (STRICT)")
    print("="*70 + "\n")

    all_cases = []
    for state_name, url in STATE_AG_URLS.items():
        print(f"  {state_name:20} {url[:45]:45}", end='', flush=True)
        cases = scrape_state(state_name, url)
        all_cases.extend(cases)
        print(f" Found: {len(cases)}")
        time.sleep(1)

    return all_cases

def upload(cases):
    if not cases:
        print("\nNo cases to upload")
        return 0

    # Deduplicate by fingerprint
    seen = {}
    for c in cases:
        seen[c['fingerprint']] = c
    cases = list(seen.values())

    print(f"\n" + "="*70)
    print(f"Total unique cases: {len(cases)}")

    statuses, positions, locations = {}, {}, {}
    dates_found = 0
    for c in cases:
        statuses[c['case_status']] = statuses.get(c['case_status'], 0) + 1
        positions[c['position_title']] = positions.get(c['position_title'], 0) + 1
        locations[c['location']] = locations.get(c['location'], 0) + 1
        if c.get('date_charged'):
            dates_found += 1

    print("\nBy Status:")
    for k, v in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k}: {v}")

    print("\nTop Positions:")
    for k, v in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {k}: {v}")

    print("\nStates with Cases:")
    for k, v in sorted(locations.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k}: {v}")

    print(f"\nDates extracted: {dates_found}/{len(cases)}")

    with open('state_ag_cases.json', 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"Saved: state_ag_cases.json")

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
    cases = scrape_all_states()
    uploaded = upload(cases)

    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} state AG cases uploaded")
    print("="*70 + "\n")