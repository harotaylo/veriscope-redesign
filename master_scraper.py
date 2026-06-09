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

STATES = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
    'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming'
]

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

USAO_TO_STATE = {
    'usao-ndal': 'Alabama', 'usao-mdal': 'Alabama', 'usao-sdal': 'Alabama',
    'usao-ak': 'Alaska',
    'usao-az': 'Arizona',
    'usao-edar': 'Arkansas', 'usao-wdar': 'Arkansas',
    'usao-cdca': 'California', 'usao-edca': 'California', 'usao-ndca': 'California', 'usao-sdca': 'California',
    'usao-co': 'Colorado',
    'usao-ct': 'Connecticut',
    'usao-de': 'Delaware',
    'usao-dc': 'District of Columbia',
    'usao-ndfl': 'Florida', 'usao-mdfl': 'Florida', 'usao-sdfl': 'Florida',
    'usao-ndga': 'Georgia', 'usao-mdga': 'Georgia', 'usao-sdga': 'Georgia',
    'usao-hi': 'Hawaii',
    'usao-id': 'Idaho',
    'usao-ndil': 'Illinois', 'usao-cdil': 'Illinois', 'usao-sdil': 'Illinois',
    'usao-ndin': 'Indiana', 'usao-sdin': 'Indiana',
    'usao-ndia': 'Iowa', 'usao-sdia': 'Iowa',
    'usao-ks': 'Kansas',
    'usao-edky': 'Kentucky', 'usao-wdky': 'Kentucky',
    'usao-edla': 'Louisiana', 'usao-mdla': 'Louisiana', 'usao-wdla': 'Louisiana',
    'usao-me': 'Maine',
    'usao-md': 'Maryland',
    'usao-ma': 'Massachusetts',
    'usao-edmi': 'Michigan', 'usao-wdmi': 'Michigan',
    'usao-mn': 'Minnesota',
    'usao-ndms': 'Mississippi', 'usao-sdms': 'Mississippi',
    'usao-edmo': 'Missouri', 'usao-wdmo': 'Missouri',
    'usao-mt': 'Montana',
    'usao-ne': 'Nebraska',
    'usao-nv': 'Nevada',
    'usao-nh': 'New Hampshire',
    'usao-nj': 'New Jersey',
    'usao-nm': 'New Mexico',
    'usao-edny': 'New York', 'usao-ndny': 'New York', 'usao-sdny': 'New York', 'usao-wdny': 'New York',
    'usao-ednc': 'North Carolina', 'usao-mdnc': 'North Carolina', 'usao-wdnc': 'North Carolina',
    'usao-nd': 'North Dakota',
    'usao-ndoh': 'Ohio', 'usao-sdoh': 'Ohio',
    'usao-edok': 'Oklahoma', 'usao-ndok': 'Oklahoma', 'usao-wdok': 'Oklahoma',
    'usao-or': 'Oregon',
    'usao-edpa': 'Pennsylvania', 'usao-mdpa': 'Pennsylvania', 'usao-wdpa': 'Pennsylvania',
    'usao-ri': 'Rhode Island',
    'usao-sc': 'South Carolina',
    'usao-sd': 'South Dakota',
    'usao-edtn': 'Tennessee', 'usao-mdtn': 'Tennessee', 'usao-wdtn': 'Tennessee',
    'usao-edtx': 'Texas', 'usao-ndtx': 'Texas', 'usao-sdtx': 'Texas', 'usao-wdtx': 'Texas',
    'usao-ut': 'Utah',
    'usao-vt': 'Vermont',
    'usao-edva': 'Virginia', 'usao-wdva': 'Virginia',
    'usao-edwa': 'Washington', 'usao-wdwa': 'Washington',
    'usao-ndwv': 'West Virginia', 'usao-sdwv': 'West Virginia',
    'usao-edwi': 'Wisconsin', 'usao-wdwi': 'Wisconsin',
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

def get_location_from_url(url):
    if not url:
        return 'Unknown'
    url_lower = url.lower()
    for code in sorted(USAO_TO_STATE.keys(), key=len, reverse=True):
        if code in url_lower:
            return USAO_TO_STATE[code]
    if '/opa/' in url_lower:
        return 'Federal'
    return 'Unknown'

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

# ================================================================
# SOURCE A: DOJ API - Federal + State-specific search terms
# ================================================================
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
                    'publication_status': 'published',
                    'verified_by': 'master_scraper_doj',
                    'verified_at': datetime.now().isoformat(),
                    'fingerprint': hashlib.md5(f"{title}_{url}".encode()).hexdigest()
                })
            except:
                continue
    except Exception as e:
        print(f"  Error: {str(e)[:60]}")
    return cases

def scrape_doj_all():
    print("\n" + "="*70)
    print("SOURCE A: DOJ API - Federal + All 50 States")
    print("="*70 + "\n")

    # Base federal terms
    base_terms = [
        'federal judge convicted', 'federal judge indicted',
        'u.s. attorney charged', 'u.s. attorney convicted',
        'senator guilty', 'senator convicted', 'senator indicted',
        'congressman convicted', 'congressman indicted', 'congressman guilty',
        'representative convicted', 'representative indicted',
        'federal prosecutor indicted', 'fbi agent convicted',
        'governor convicted', 'governor indicted', 'governor guilty',
        'mayor convicted', 'mayor indicted',
        'sheriff convicted', 'sheriff indicted', 'deputy sheriff convicted',
        'police chief indicted', 'police chief convicted',
        'city council convicted', 'city council guilty',
        'district attorney guilty', 'district attorney convicted',
        'county commissioner convicted', 'county judge charged',
        'alderman guilty', 'fire chief convicted',
    ]

    # State-specific terms for all 50 states
    state_terms = []
    for state in STATES:
        state_terms.extend([
            f'{state} official convicted',
            f'{state} senator convicted',
            f'{state} mayor indicted',
            f'{state} sheriff guilty',
            f'{state} police chief convicted',
        ])

    all_terms = base_terms + state_terms
    all_cases = []

    for term in all_terms:
        print(f"  {term:50}", end='', flush=True)
        cases = scrape_doj(term)
        all_cases.extend(cases)
        print(f" Found: {len(cases)}")
        time.sleep(0.3)

    return all_cases

# ================================================================
# SOURCE B: Google News RSS - State AG press releases
# ================================================================
def scrape_google_news(state):
    cases = []
    try:
        query = f'{state} official convicted OR indicted OR guilty site:ag.gov OR site:ago.gov OR site:doj.gov'
        url = f'https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en'

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        resp = requests.get(url, timeout=10, headers=headers)
        if resp.status_code != 200:
            return cases

        soup = BeautifulSoup(resp.text, 'xml')
        items = soup.find_all('item')[:20]

        for item in items:
            try:
                title = item.find('title')
                title = title.get_text(strip=True) if title else ''
                desc = item.find('description')
                desc = desc.get_text(strip=True) if desc else ''
                link = item.find('link')
                link = link.get_text(strip=True) if link else ''
                pub_date = item.find('pubDate')
                pub_date = pub_date.get_text(strip=True) if pub_date else ''

                if not title or len(title) < 10:
                    continue

                if not is_official(title, desc):
                    continue

                combined = f"{title} {desc}"

                cases.append({
                    'full_name': get_name(title),
                    'title': title[:150],
                    'position_title': get_position(combined),
                    'official_type': get_official_type(combined),
                    'location': state,
                    'level': get_level(combined),
                    'category': 'Corruption',
                    'abuse_of_power_type': 'Corruption',
                    'case_status': get_status(combined),
                    'date_charged': extract_date(combined) or extract_date(pub_date),
                    'details': desc[:1000],
                    'source_url': link,
                    'source_type': 'court_record',
                    'source_date': str(datetime.now().date()),
                    'publication_status': 'published',
                    'verified_by': 'master_scraper_news',
                    'verified_at': datetime.now().isoformat(),
                    'fingerprint': hashlib.md5(f"{title}_{state}".encode()).hexdigest()
                })
            except:
                continue

        return cases
    except:
        return cases

def scrape_google_news_all():
    print("\n" + "="*70)
    print("SOURCE B: Google News RSS - All 50 States")
    print("="*70 + "\n")

    all_cases = []
    for state in STATES:
        print(f"  {state:20}", end='', flush=True)
        cases = scrape_google_news(state)
        all_cases.extend(cases)
        print(f" Found: {len(cases)}")
        time.sleep(1)

    return all_cases

# ================================================================
# UPLOAD
# ================================================================
def upload(cases, source_label):
    if not cases:
        print(f"\nNo cases from {source_label}")
        return 0

    # Deduplicate by fingerprint
    seen = {}
    for c in cases:
        seen[c['fingerprint']] = c
    cases = list(seen.values())

    print(f"\n" + "="*70)
    print(f"{source_label}: {len(cases)} unique cases")

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
    for k, v in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {k}: {v}")

    print("\nTop Locations:")
    for k, v in sorted(locations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {k}: {v}")

    print(f"\nDates extracted: {dates_found}/{len(cases)}")

    filename = f"{source_label.lower().replace(' ', '_')}_cases.json"
    with open(filename, 'w') as f:
        json.dump(cases, f, indent=2)
    print(f"Saved: {filename}")

    print(f"\nUploading to Supabase...")

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
    print("\n" + "="*70)
    print("VERISCOPE MASTER SCRAPER")
    print("DOJ API + Google News RSS - All 50 States")
    print("="*70)

    # Source A: DOJ API
    doj_cases = scrape_doj_all()
    doj_uploaded = upload(doj_cases, "DOJ API")

    # Source B: Google News RSS
    news_cases = scrape_google_news_all()
    news_uploaded = upload(news_cases, "Google News")

    print(f"\n" + "="*70)
    print(f"MASTER SCRAPER COMPLETE")
    print(f"  DOJ API uploaded:    {doj_uploaded}")
    print(f"  Google News uploaded: {news_uploaded}")
    print(f"  Total uploaded:       {doj_uploaded + news_uploaded}")
    print("="*70 + "\n")