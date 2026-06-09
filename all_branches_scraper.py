#!/usr/bin/env python3
"""
VeriScope All-Branches Public Official Misconduct Scraper
Covers Executive, Legislative, and Judicial branches at all levels.
Sources: DOJ API (paginated), FBI RSS, OIG reports (DOJ/HHS/DHS/VA), State AGs
"""

import json
import requests
import hashlib
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

SUPABASE_URL = 'https://sqaibfaniwbixviptilx.supabase.co'
SUPABASE_KEY = 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ'

STATES = [
    'Alabama','Alaska','Arizona','Arkansas','California','Colorado',
    'Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho',
    'Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana',
    'Maine','Maryland','Massachusetts','Michigan','Minnesota',
    'Mississippi','Missouri','Montana','Nebraska','Nevada',
    'New Hampshire','New Jersey','New Mexico','New York',
    'North Carolina','North Dakota','Ohio','Oklahoma','Oregon',
    'Pennsylvania','Rhode Island','South Carolina','South Dakota',
    'Tennessee','Texas','Utah','Vermont','Virginia','Washington',
    'West Virginia','Wisconsin','Wyoming'
]

# ============================================================
# OFFICIAL KEYWORDS - All Branches
# ============================================================

JUDICIAL_FEDERAL = [
    'chief justice', 'supreme court justice', 'associate justice',
    'circuit judge', 'appeals court judge', 'appellate judge',
    'district judge', 'federal district judge', 'u.s. district judge',
    'magistrate judge', 'u.s. magistrate', 'bankruptcy judge',
    'administrative law judge', 'immigration judge', 'tax court judge',
    'federal judge',
]

JUDICIAL_STATE = [
    'state supreme court justice', 'state appellate judge',
    'superior court judge', 'circuit court judge', 'state circuit judge',
    'state district judge', 'district court judge', 'county court judge',
    'family court judge', 'probate judge', 'juvenile court judge',
    'municipal court judge', 'city court judge', 'traffic court judge',
    'justice of the peace', 'magistrate', 'court commissioner',
    'court administrator', 'clerk of court', 'state judge',
]

LEGISLATIVE_FEDERAL = [
    'u.s. senator', 'united states senator', 'senator',
    'u.s. representative', 'u.s. congressman', 'u.s. congresswoman',
    'congressman', 'congresswoman', 'representative',
    'house speaker', 'senate majority leader', 'congressional staffer',
]

LEGISLATIVE_STATE = [
    'state senator', 'state representative',
    'state assemblyman', 'state assemblywoman', 'state assembly member',
    'state delegate', 'state lawmaker', 'state legislator',
    'state house member', 'general assembly member',
    'state house speaker', 'state senate president',
]

LEGISLATIVE_LOCAL = [
    'city council member', 'city councilman', 'city councilwoman', 'city councilmember',
    'county commissioner', 'county board member', 'county supervisor',
    'alderman', 'alderwoman',
    'town council member', 'town selectman', 'village trustee',
    'school board member', 'school board director', 'school board trustee',
    'water board member', 'port commissioner', 'transit board member',
    'housing authority board member', 'city council',
]

EXECUTIVE_FEDERAL = [
    'president', 'vice president',
    'cabinet secretary', 'secretary of defense', 'secretary of homeland security',
    'attorney general', 'secretary of treasury',
    'agency director', 'bureau director', 'federal director',
    'white house official', 'white house staffer', 'presidential advisor',
    'u.s. attorney', 'assistant u.s. attorney', 'federal prosecutor',
    'federal official', 'federal administrator',
]

EXECUTIVE_STATE = [
    'governor', 'lieutenant governor',
    'state attorney general', 'state treasurer', 'state auditor',
    'state comptroller', 'state controller', 'state inspector general',
    'state secretary of state', 'state insurance commissioner',
    'state corrections director', 'state department director',
    'state agency director', 'state administrator', 'state official',
]

EXECUTIVE_LOCAL = [
    'mayor', 'deputy mayor', 'city manager', 'town manager', 'county manager',
    'county executive', 'county administrator', 'city administrator',
    'city clerk', 'town clerk', 'city comptroller', 'city treasurer',
    'city auditor', 'city attorney', 'county attorney',
    'public administrator', 'register of deeds',
    'fire chief', 'fire commissioner',
    'police chief', 'deputy police chief', 'police commissioner',
    'city official', 'local official', 'municipal official',
]

LAW_ENFORCEMENT_FEDERAL = [
    'fbi agent', 'fbi special agent',
    'dea agent', 'dea special agent',
    'atf agent', 'atf special agent',
    'ice agent', 'ice officer', 'immigration enforcement agent',
    'border patrol agent', 'customs officer', 'cbp officer',
    'u.s. marshal', 'deputy marshal', 'federal marshal',
    'secret service agent', 'secret service officer',
    'hsi agent', 'postal inspector', 'tsa officer',
    'capitol police officer', 'park police officer',
    'irs agent', 'federal officer', 'federal agent',
]

LAW_ENFORCEMENT_STATE = [
    'state trooper', 'state police officer', 'highway patrol officer',
    'state investigator', 'state bureau of investigation agent',
    'state correctional officer', 'state corrections officer',
]

LAW_ENFORCEMENT_LOCAL = [
    'sheriff', 'county sheriff', 'deputy sheriff',
    'police officer', 'police detective', 'police sergeant', 'police lieutenant',
    'police captain', 'police investigator',
    'constable', 'deputy constable',
    'correctional officer', 'jail officer', 'detention officer',
    'prison guard', 'prison warden', 'jail warden',
    'probation officer', 'parole officer',
    'school resource officer', 'transit police officer',
    'former officer', 'former deputy', 'former detective', 'former trooper',
]

ALL_OFFICIALS = (
    JUDICIAL_FEDERAL + JUDICIAL_STATE +
    LEGISLATIVE_FEDERAL + LEGISLATIVE_STATE + LEGISLATIVE_LOCAL +
    EXECUTIVE_FEDERAL + EXECUTIVE_STATE + EXECUTIVE_LOCAL +
    LAW_ENFORCEMENT_FEDERAL + LAW_ENFORCEMENT_STATE + LAW_ENFORCEMENT_LOCAL
)

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty plea', 'pleaded guilty', 'pled guilty', 'pleads guilty',
    'plead guilty', 'indicted', 'grand jury', 'charged with', 'charges filed',
    'arrested for', 'sentenced to', 'sentenced for',
    'removed from office', 'suspended', 'censured', 'disbarred', 'impeached',
    'corruption', 'bribery', 'extortion', 'kickback',
    'fraud', 'embezzlement', 'theft', 'larceny', 'misappropriation',
    'money laundering', 'wire fraud', 'mail fraud', 'tax evasion',
    'obstruction', 'perjury', 'false statement',
    'civil rights violation', 'excessive force', 'deprivation of rights',
    'drug trafficking', 'narcotics', 'conspiracy',
    'sexual assault', 'sexual misconduct', 'rape',
    'child pornography', 'csam', 'child exploitation', 'sex trafficking',
    'racketeering', 'rico', 'abuse of office', 'official misconduct',
]

# Use whole-word patterns to avoid matching "convicted" for "convict", etc.
EXCLUDE_PATTERNS = [
    r'\bgang member\b', r'\bdrug dealer\b', r'\bfelon\b', r'\bbusinessman\b',
    r'\bactivist\b', r'\bprivate citizen\b', r'\bbusiness owner\b',
    r'\bterrorist\b', r'\bal-qaeda\b', r'\bisis\b', r'\bjihad\b',
    r'\bmilitia member\b', r'\binmate\b', r'\bprisoner\b',
    r'\bconvict\b',  # word-boundary: won't match "convicted"
    r'\bfugitive\b', r'\bsmuggler\b', r'\btrafficker\b',
    r'\bhacker\b', r'\bfraudster\b', r'\bscammer\b',
]

VICTIM_PATTERNS = [
    'plotting to murder', 'plot to kill', 'plot to murder',
    'threat against judge', 'threat against officer', 'threat against official',
    'targeting judge', 'targeting officer', 'man charged with killing',
    'woman charged with killing', 'charged with murdering officer',
    'indicted for killing judge', 'sentenced for murdering',
    'for killing a police', 'for killing the officer',
    'attempted assassination of',
]

# ============================================================
# DOJ API SEARCH TERMS - All Branches, All Levels
# ============================================================

DOJ_SEARCH_TERMS = [
    # Judicial - Federal
    'federal judge convicted', 'federal judge indicted', 'federal judge charged',
    'federal judge guilty', 'federal judge arrested',
    'district judge convicted', 'district judge indicted',
    'circuit judge convicted', 'circuit judge indicted',
    'magistrate judge convicted', 'magistrate judge indicted', 'magistrate judge charged',
    'bankruptcy judge convicted', 'bankruptcy judge indicted',
    'immigration judge convicted', 'immigration judge indicted',
    'administrative law judge convicted',

    # Judicial - State/Local
    'state judge convicted', 'state judge indicted', 'state judge charged',
    'superior court judge convicted', 'superior court judge indicted',
    'county court judge convicted', 'county judge charged', 'county judge convicted',
    'municipal court judge convicted', 'family court judge convicted',
    'probate judge convicted', 'magistrate convicted', 'magistrate indicted',
    'clerk of court convicted', 'court commissioner convicted',

    # Legislative - Federal
    'senator convicted', 'senator indicted', 'senator guilty', 'senator charged',
    'senator arrested', 'senator sentenced',
    'congressman convicted', 'congressman indicted', 'congressman guilty',
    'congresswoman convicted', 'congresswoman indicted',
    'representative convicted', 'representative indicted', 'representative guilty',
    'u.s. representative indicted', 'u.s. senator convicted',

    # Legislative - State
    'state senator convicted', 'state senator indicted', 'state senator guilty',
    'state senator charged', 'state senator arrested',
    'state representative convicted', 'state representative indicted',
    'state assemblyman convicted', 'state assemblyman indicted',
    'state assemblywoman convicted', 'state assemblywoman indicted',
    'state delegate convicted', 'state delegate indicted',
    'state lawmaker convicted', 'state lawmaker indicted',
    'state legislator convicted', 'state legislator indicted',

    # Legislative - Local
    'city council convicted', 'city council indicted', 'city council guilty',
    'city councilman convicted', 'city councilman indicted',
    'city councilwoman convicted', 'alderman convicted', 'alderman indicted',
    'alderman guilty', 'alderwoman convicted',
    'county commissioner convicted', 'county commissioner indicted', 'county commissioner guilty',
    'county board member convicted', 'county supervisor convicted',
    'school board member convicted', 'school board member indicted',
    'school board convicted',

    # Executive - Federal
    'u.s. attorney convicted', 'u.s. attorney indicted', 'u.s. attorney charged',
    'assistant u.s. attorney convicted', 'federal prosecutor indicted',
    'federal prosecutor convicted', 'federal official convicted',
    'federal official indicted', 'white house official indicted',
    'cabinet secretary convicted',

    # Executive - State
    'governor convicted', 'governor indicted', 'governor guilty', 'governor charged',
    'governor arrested', 'governor sentenced',
    'lieutenant governor convicted', 'lieutenant governor indicted',
    'state attorney general convicted', 'state attorney general indicted',
    'state treasurer convicted', 'state treasurer indicted',
    'state auditor convicted', 'state auditor indicted',
    'state comptroller convicted', 'state controller convicted',
    'state official convicted', 'state official indicted', 'state official guilty',

    # Executive - Local
    'mayor convicted', 'mayor indicted', 'mayor guilty', 'mayor charged',
    'mayor arrested', 'mayor sentenced',
    'deputy mayor convicted', 'city manager convicted', 'city manager indicted',
    'county manager convicted', 'county executive convicted',
    'city clerk convicted', 'city treasurer convicted', 'city auditor convicted',
    'city comptroller convicted', 'city attorney convicted',
    'county attorney convicted', 'public administrator convicted',
    'fire chief convicted', 'fire chief indicted',
    'police chief indicted', 'police chief convicted', 'police chief charged',
    'deputy police chief convicted',

    # Law Enforcement - Federal
    'fbi agent convicted', 'fbi agent indicted', 'fbi agent guilty',
    'fbi agent charged', 'fbi agent arrested',
    'dea agent convicted', 'dea agent indicted', 'dea agent guilty',
    'atf agent convicted', 'atf agent indicted', 'atf agent charged',
    'ice agent convicted', 'ice officer convicted', 'ice officer indicted',
    'border patrol agent convicted', 'border patrol agent indicted',
    'customs officer convicted', 'cbp officer convicted',
    'u.s. marshal convicted', 'deputy marshal convicted',
    'secret service agent convicted', 'secret service officer convicted',
    'postal inspector convicted', 'tsa officer convicted',
    'irs agent convicted', 'federal agent convicted', 'federal officer convicted',

    # Law Enforcement - State
    'state trooper convicted', 'state trooper indicted', 'state trooper guilty',
    'state trooper charged', 'state trooper arrested',
    'state police officer convicted', 'state police officer indicted',
    'highway patrol officer convicted',

    # Law Enforcement - Local
    'sheriff convicted', 'sheriff indicted', 'sheriff guilty', 'sheriff charged',
    'sheriff arrested', 'sheriff sentenced',
    'deputy sheriff convicted', 'deputy sheriff indicted', 'deputy sheriff guilty',
    'deputy sheriff charged', 'deputy sheriff arrested',
    'police officer convicted', 'police officer indicted', 'police officer guilty',
    'police officer charged', 'police officer sentenced',
    'police detective convicted', 'police detective indicted',
    'constable convicted', 'constable indicted',
    'correctional officer convicted', 'correctional officer indicted',
    'correctional officer charged', 'jail officer convicted',
    'prison guard convicted', 'prison warden convicted',
    'probation officer convicted', 'probation officer indicted',
    'parole officer convicted', 'parole officer indicted',

    # Crime type searches
    'public official bribery', 'official bribery convicted',
    'corruption government official', 'corruption public official',
    'embezzlement public official', 'theft public funds',
    'civil rights officer convicted', 'excessive force convicted',
    'drug trafficking officer', 'drug trafficking sheriff',
    'sex trafficking officer', 'csam officer convicted',
    'child pornography officer convicted', 'child exploitation officer',
    'official fraud convicted', 'corruption convicted official',
]

# State-specific terms to broaden geographic coverage
STATE_DOJ_TERMS = []
for state in STATES:
    STATE_DOJ_TERMS.extend([
        f'{state} official convicted',
        f'{state} official indicted',
        f'{state} senator convicted',
        f'{state} mayor indicted',
        f'{state} sheriff guilty',
        f'{state} police chief convicted',
        f'{state} judge convicted',
        f'{state} governor indicted',
    ])

ALL_DOJ_TERMS = DOJ_SEARCH_TERMS + STATE_DOJ_TERMS

# ============================================================
# OIG RSS FEEDS - Office of Inspector General
# ============================================================

OIG_FEEDS = {
    'DOJ OIG': 'https://oig.justice.gov/feeds/oig-news.xml',
    'HHS OIG': 'https://oig.hhs.gov/rss/oig-newsroom.xml',
    'DHS OIG': 'https://www.oig.dhs.gov/rss/news-releases-rss.xml',
    'VA OIG': 'https://www.va.gov/oig/rss/news-releases-rss.xml',
    'DOD IG': 'https://www.dodig.mil/rss/news-releases-rss.xml',
}

# FBI news (their atom feed)
FBI_FEED = 'https://www.fbi.gov/feeds/fbi-in-the-news/atom.xml'

# ============================================================
# HELPERS
# ============================================================

MONTHS = {
    'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
    'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
    'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,'aug':8,
    'sep':9,'oct':10,'nov':11,'dec':12
}

SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; VeriScope-Research-Bot/1.0)'})


def extract_date(text):
    if not text:
        return None
    text = text.replace('\n', ' ')
    m = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December|'
        r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})',
        text, re.IGNORECASE
    )
    if m:
        mo = MONTHS.get(m.group(1).lower(), 1)
        try:
            return f"{int(m.group(3)):04d}-{mo:02d}-{int(m.group(2)):02d}"
        except Exception:
            pass
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if m:
        return f"{m.group(1)}-{m.group(2):0>2}-{m.group(3):0>2}"
    return None


def html_to_text(html):
    if not html:
        return ''
    return BeautifulSoup(html, 'lxml').get_text(separator=' ', strip=True)


def contains_any(text, kws):
    t = text.lower()
    return any(k in t for k in kws)


def is_official(title, body):
    combined = f"{title} {body}".lower()
    title_lower = title.lower()
    if not contains_any(combined, ALL_OFFICIALS):
        return False
    if any(p in title_lower for p in VICTIM_PATTERNS):
        return False
    if any(re.search(pat, combined) for pat in EXCLUDE_PATTERNS):
        return False
    if not contains_any(combined, MISCONDUCT_KEYWORDS):
        return False
    return True


def get_branch(text):
    t = text.lower()
    if contains_any(t, JUDICIAL_FEDERAL + JUDICIAL_STATE):
        return 'Judicial'
    if contains_any(t, LEGISLATIVE_FEDERAL + LEGISLATIVE_STATE + LEGISLATIVE_LOCAL):
        return 'Legislative'
    if contains_any(t, LAW_ENFORCEMENT_FEDERAL + LAW_ENFORCEMENT_STATE + LAW_ENFORCEMENT_LOCAL):
        return 'Law Enforcement'
    return 'Executive'


def get_level(text):
    t = text.lower()
    if contains_any(t, JUDICIAL_FEDERAL + LEGISLATIVE_FEDERAL + EXECUTIVE_FEDERAL + LAW_ENFORCEMENT_FEDERAL):
        return 'Federal'
    if contains_any(t, JUDICIAL_STATE + LEGISLATIVE_STATE + EXECUTIVE_STATE + LAW_ENFORCEMENT_STATE):
        return 'State'
    if contains_any(t, LEGISLATIVE_LOCAL + EXECUTIVE_LOCAL + LAW_ENFORCEMENT_LOCAL):
        if contains_any(t, ['county', 'county commissioner', 'deputy sheriff', 'county judge']):
            return 'County'
        return 'City'
    return 'State'


def get_position(text):
    t = text.lower()
    # Judicial
    if 'chief justice' in t or 'supreme court justice' in t: return 'Supreme Court Justice'
    if 'circuit judge' in t or 'appeals court judge' in t: return 'Circuit/Appeals Judge'
    if 'district judge' in t or 'federal district judge' in t: return 'District Judge'
    if 'magistrate judge' in t or 'u.s. magistrate' in t: return 'Magistrate Judge'
    if 'bankruptcy judge' in t: return 'Bankruptcy Judge'
    if 'immigration judge' in t: return 'Immigration Judge'
    if 'administrative law judge' in t: return 'Administrative Law Judge'
    if 'superior court judge' in t: return 'Superior Court Judge'
    if 'county court judge' in t or 'county judge' in t: return 'County Judge'
    if 'municipal court judge' in t: return 'Municipal Court Judge'
    if 'family court judge' in t: return 'Family Court Judge'
    if 'probate judge' in t: return 'Probate Judge'
    if 'magistrate' in t: return 'Magistrate'
    if 'clerk of court' in t: return 'Clerk of Court'
    if 'federal judge' in t or 'state judge' in t or 'judge' in t: return 'Judge'
    # Legislative
    if 'u.s. senator' in t or ('senator' in t and 'state senator' not in t): return 'U.S. Senator'
    if 'congressman' in t or 'congresswoman' in t or 'u.s. representative' in t: return 'Congressman/woman'
    if 'representative' in t and 'state' not in t: return 'U.S. Representative'
    if 'state senator' in t: return 'State Senator'
    if 'state representative' in t: return 'State Representative'
    if 'state assemblyman' in t or 'state assemblywoman' in t or 'state assembly member' in t: return 'State Assembly Member'
    if 'state delegate' in t: return 'State Delegate'
    if 'state lawmaker' in t or 'state legislator' in t: return 'State Legislator'
    if 'city councilman' in t or 'city councilwoman' in t or 'city councilmember' in t or 'city council member' in t: return 'City Council Member'
    if 'alderman' in t or 'alderwoman' in t: return 'Alderman'
    if 'county commissioner' in t: return 'County Commissioner'
    if 'county supervisor' in t: return 'County Supervisor'
    if 'county board member' in t: return 'County Board Member'
    if 'school board member' in t or 'school board director' in t: return 'School Board Member'
    if 'city council' in t: return 'City Council Member'
    # Executive - Federal
    if 'vice president' in t: return 'Vice President'
    if 'president' in t and 'vice' not in t: return 'President'
    if 'cabinet secretary' in t: return 'Cabinet Secretary'
    if 'u.s. attorney' in t or 'us attorney' in t: return 'U.S. Attorney'
    if 'assistant u.s. attorney' in t: return 'Assistant U.S. Attorney'
    if 'federal prosecutor' in t: return 'Federal Prosecutor'
    if 'white house official' in t: return 'White House Official'
    if 'federal official' in t or 'federal administrator' in t: return 'Federal Official'
    # Executive - State
    if 'lieutenant governor' in t: return 'Lieutenant Governor'
    if 'governor' in t: return 'Governor'
    if 'state attorney general' in t: return 'State Attorney General'
    if 'state treasurer' in t: return 'State Treasurer'
    if 'state auditor' in t: return 'State Auditor'
    if 'state comptroller' in t or 'state controller' in t: return 'State Comptroller'
    if 'state official' in t: return 'State Official'
    # Executive - Local
    if 'deputy mayor' in t: return 'Deputy Mayor'
    if 'mayor' in t: return 'Mayor'
    if 'city manager' in t or 'town manager' in t: return 'City Manager'
    if 'county manager' in t or 'county executive' in t: return 'County Executive'
    if 'city attorney' in t or 'county attorney' in t: return 'City/County Attorney'
    if 'city clerk' in t or 'town clerk' in t: return 'City Clerk'
    if 'city comptroller' in t or 'city treasurer' in t: return 'City Treasurer'
    if 'fire chief' in t or 'fire commissioner' in t: return 'Fire Chief'
    if 'deputy police chief' in t: return 'Deputy Police Chief'
    if 'police chief' in t or 'police commissioner' in t: return 'Police Chief'
    # Law Enforcement - Federal
    if 'fbi agent' in t or 'fbi special agent' in t: return 'FBI Agent'
    if 'dea agent' in t or 'dea special agent' in t: return 'DEA Agent'
    if 'atf agent' in t or 'atf special agent' in t: return 'ATF Agent'
    if 'ice agent' in t or 'ice officer' in t: return 'ICE Agent/Officer'
    if 'border patrol agent' in t: return 'Border Patrol Agent'
    if 'customs officer' in t or 'cbp officer' in t: return 'CBP/Customs Officer'
    if 'u.s. marshal' in t or 'deputy marshal' in t: return 'U.S. Marshal'
    if 'secret service agent' in t or 'secret service officer' in t: return 'Secret Service Agent'
    if 'postal inspector' in t: return 'Postal Inspector'
    if 'tsa officer' in t: return 'TSA Officer'
    if 'irs agent' in t: return 'IRS Agent'
    if 'federal agent' in t or 'federal officer' in t: return 'Federal Agent/Officer'
    # Law Enforcement - State/Local
    if 'state trooper' in t: return 'State Trooper'
    if 'state police officer' in t: return 'State Police Officer'
    if 'highway patrol' in t: return 'Highway Patrol Officer'
    if 'deputy sheriff' in t: return 'Deputy Sheriff'
    if 'county sheriff' in t or 'sheriff' in t: return 'Sheriff'
    if 'police detective' in t: return 'Police Detective'
    if 'constable' in t: return 'Constable'
    if 'prison warden' in t or 'jail warden' in t: return 'Prison/Jail Warden'
    if 'prison guard' in t or 'jail officer' in t or 'detention officer' in t: return 'Correctional/Detention Officer'
    if 'correctional officer' in t: return 'Correctional Officer'
    if 'probation officer' in t: return 'Probation Officer'
    if 'parole officer' in t: return 'Parole Officer'
    if 'police officer' in t or 'police' in t or 'officer' in t: return 'Police Officer'
    return 'Public Official'


def get_status(text):
    t = text.lower()
    if any(k in t for k in ['acquitted', 'not guilty', 'found not guilty']): return 'Acquitted'
    if any(k in t for k in ['convicted', 'found guilty', 'guilty verdict']): return 'Convicted'
    if any(k in t for k in ['sentenced to', 'sentenced for', 'sentencing']): return 'Convicted'
    if any(k in t for k in ['pleaded guilty', 'pled guilty', 'guilty plea', 'plead guilty', 'pleads guilty']): return 'Convicted'
    if any(k in t for k in ['indicted', 'grand jury indicted', 'grand jury returned']): return 'Indicted'
    if any(k in t for k in ['charged with', 'charges filed', 'arrested for', 'faces charges']): return 'Indicted'
    if any(k in t for k in ['dismissed', 'charges dropped', 'case dismissed']): return 'Dismissed'
    if 'suspended' in t or 'removed from office' in t: return 'Dismissed'
    return 'Indicted'


def get_abuse_type(text):
    t = text.lower()
    if any(k in t for k in ['csam', 'child pornography', 'child exploitation', 'child sexual abuse', 'sex trafficking of a minor']): return 'CSAM/Child Exploitation'
    if any(k in t for k in ['bribery', 'kickback', 'extortion', 'quid pro quo']): return 'Bribery/Extortion'
    if any(k in t for k in ['fraud', 'embezzlement', 'theft', 'larceny', 'wire fraud', 'mail fraud', 'misappropriation']): return 'Fraud/Embezzlement'
    if any(k in t for k in ['civil rights', 'excessive force', 'deprivation of rights', 'color of law']): return 'Civil Rights Violation'
    if any(k in t for k in ['drug trafficking', 'drug distribution', 'narcotics', 'fentanyl', 'cocaine', 'meth']): return 'Drug Trafficking'
    if any(k in t for k in ['obstruction', 'perjury', 'false statement', 'evidence tampering']): return 'Obstruction/Perjury'
    if any(k in t for k in ['sexual assault', 'rape', 'sex offense', 'sexual misconduct', 'sex trafficking']): return 'Sexual Misconduct'
    if any(k in t for k in ['money laundering', 'money laundering']): return 'Money Laundering'
    if any(k in t for k in ['tax evasion', 'tax fraud']): return 'Tax Evasion'
    if any(k in t for k in ['racketeering', 'rico', 'organized crime']): return 'Racketeering'
    return 'Corruption'


def get_name(title):
    title = re.sub(r'^(Former|Retired|Ex-|Disgraced|Convicted|Indicted|Corrupt)\s+', '', title, flags=re.IGNORECASE).strip()
    if ' - ' in title:
        candidate = title.split(' - ')[0].strip()
        if 3 < len(candidate) < 80:
            return candidate
    for verb in ['Convicted', 'Charged', 'Indicted', 'Sentenced', 'Plead', 'Pleads', 'Arrested', 'Guilty']:
        if verb in title:
            candidate = title.split(verb)[0].strip()
            if 3 < len(candidate) < 80:
                return candidate
    # Try to extract a name-like pattern: "First Last, Title"
    m = re.match(r'^([A-Z][a-z]+ (?:[A-Z]\. )?[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)', title)
    if m:
        return m.group(1)
    return 'Unknown Official'


def make_fingerprint(*parts):
    return hashlib.md5('_'.join(str(p) for p in parts).encode()).hexdigest()


def build_case(title, body, url, location, source_label):
    combined = f"{title} {body}"
    return {
        'full_name': get_name(title),
        'title': title[:200],
        'position_title': get_position(combined),
        'official_type': get_branch(combined),
        'location': location,
        'level': get_level(combined),
        'category': 'Public Official Misconduct',
        'abuse_of_power_type': get_abuse_type(combined),
        'case_status': get_status(combined),
        'date_charged': extract_date(combined),
        'details': body[:2000],
        'source_url': url,
        'source_type': 'official_report',
        'source_date': str(datetime.now().date()),
        'publication_status': 'draft',
        'verified_by': source_label,
        'verified_at': datetime.now().isoformat(),
        'fingerprint': make_fingerprint(title, url or location),
    }


# ============================================================
# SOURCE A: DOJ API (paginated, up to 5 pages per term)
# ============================================================

def scrape_doj_term(term, max_pages=5):
    cases = []
    for page in range(max_pages):
        try:
            resp = SESSION.get(
                'https://www.justice.gov/api/v1/press_releases.json',
                params={'parameters[title]': term, 'pagesize': 100, 'page': page,
                        'sort': 'date', 'direction': 'DESC'},
                timeout=15
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            results = data.get('results', [])
            if not results:
                break

            for r in results:
                try:
                    title = r.get('title', '').strip()
                    body = html_to_text(r.get('body', ''))
                    url = r.get('url', '')
                    if url and not url.startswith('http'):
                        url = 'https://www.justice.gov' + url
                    if not title:
                        continue
                    if not is_official(title, body):
                        continue
                    # Extract state from USAO component
                    location = 'Federal'
                    for comp in r.get('component', []):
                        name = comp.get('name', '') if isinstance(comp, dict) else str(comp)
                        if 'USAO' in name:
                            location = name.replace('USAO - ', '').strip()
                            break

                    cases.append(build_case(title, body, url, location, 'doj_api'))
                except Exception:
                    continue

            if len(results) < 100:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"    DOJ error page {page}: {str(e)[:60]}")
            break
    return cases


def scrape_doj_all():
    print('\n' + '='*70)
    print('SOURCE A: DOJ API - All Branches, All Levels (paginated)')
    print('='*70 + '\n')
    all_cases = []
    total = len(ALL_DOJ_TERMS)
    for i, term in enumerate(ALL_DOJ_TERMS):
        print(f'  [{i+1}/{total}] {term:55}', end='', flush=True)
        cases = scrape_doj_term(term)
        all_cases.extend(cases)
        print(f' {len(cases)}')
        time.sleep(0.3)
    return all_cases


# ============================================================
# SOURCE B: FBI News Atom Feed
# ============================================================

def scrape_fbi_feed():
    print('\n' + '='*70)
    print('SOURCE B: FBI News/Press Releases')
    print('='*70 + '\n')
    cases = []
    try:
        resp = SESSION.get(FBI_FEED, timeout=15)
        if resp.status_code != 200:
            print(f'  FBI feed error: {resp.status_code}')
            return cases
        soup = BeautifulSoup(resp.text, 'xml')
        entries = soup.find_all('entry')
        print(f'  FBI feed: {len(entries)} entries')
        for entry in entries:
            try:
                title_tag = entry.find('title')
                title = title_tag.get_text(strip=True) if title_tag else ''
                summary_tag = entry.find('summary') or entry.find('content')
                body = html_to_text(summary_tag.get_text(strip=True) if summary_tag else '')
                link_tag = entry.find('link')
                url = link_tag.get('href', '') if link_tag else ''
                if not title:
                    continue
                if not is_official(title, body):
                    continue
                cases.append(build_case(title, body, url, 'Federal', 'fbi_news'))
                print(f'    [+] {title[:70]}')
            except Exception:
                continue
    except Exception as e:
        print(f'  FBI error: {str(e)[:80]}')
    print(f'  Total from FBI: {len(cases)}')
    return cases


# ============================================================
# SOURCE C: OIG Feeds (DOJ, HHS, DHS, VA, DOD)
# ============================================================

def scrape_oig_feed(name, feed_url):
    cases = []
    try:
        resp = SESSION.get(feed_url, timeout=15)
        if resp.status_code != 200:
            return cases
        soup = BeautifulSoup(resp.text, 'xml')
        items = soup.find_all('item') or soup.find_all('entry')
        for item in items:
            try:
                title_tag = item.find('title')
                title = title_tag.get_text(strip=True) if title_tag else ''
                desc_tag = item.find('description') or item.find('summary') or item.find('content')
                body = html_to_text(desc_tag.get_text(strip=True) if desc_tag else '')
                link_tag = item.find('link')
                url = ''
                if link_tag:
                    url = link_tag.get('href', '') or link_tag.get_text(strip=True)
                if not title:
                    continue
                if not is_official(title, body):
                    continue
                cases.append(build_case(title, body, url, 'Federal', f'oig_{name.lower().replace(" ", "_")}'))
                print(f'    [+] {title[:70]}')
            except Exception:
                continue
    except Exception as e:
        print(f'    {name} OIG error: {str(e)[:60]}')
    return cases


def scrape_all_oig():
    print('\n' + '='*70)
    print('SOURCE C: OIG Reports (DOJ / HHS / DHS / VA / DOD)')
    print('='*70 + '\n')
    all_cases = []
    for name, url in OIG_FEEDS.items():
        print(f'  {name}: {url[:55]}')
        cases = scrape_oig_feed(name, url)
        all_cases.extend(cases)
        print(f'  -> {len(cases)} cases')
        time.sleep(1)
    return all_cases


# ============================================================
# SOURCE D: Google News RSS (state-level)
# ============================================================

def scrape_google_news_state(state):
    cases = []
    try:
        query = (
            f'"{state}" (senator OR mayor OR sheriff OR judge OR "police officer" OR '
            f'"city council" OR "county commissioner" OR governor OR "state representative") '
            f'(convicted OR indicted OR charged OR guilty OR arrested) -"sentenced a" -"sentenced the"'
        )
        url = f'https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en'
        resp = SESSION.get(url, timeout=10)
        if resp.status_code != 200:
            return cases
        soup = BeautifulSoup(resp.text, 'xml')
        for item in soup.find_all('item')[:30]:
            try:
                title_tag = item.find('title')
                title = title_tag.get_text(strip=True) if title_tag else ''
                desc_tag = item.find('description')
                body = html_to_text(desc_tag.get_text(strip=True) if desc_tag else '')
                link_tag = item.find('link')
                link = link_tag.get_text(strip=True) if link_tag else ''
                pub_tag = item.find('pubDate')
                pub_date = pub_tag.get_text(strip=True) if pub_tag else ''
                if not title or len(title) < 10:
                    continue
                if not is_official(title, body):
                    continue
                case = build_case(title, body, link, state, 'google_news')
                if not case['date_charged']:
                    case['date_charged'] = extract_date(pub_date)
                cases.append(case)
            except Exception:
                continue
    except Exception:
        pass
    return cases


def scrape_google_news_all():
    print('\n' + '='*70)
    print('SOURCE D: Google News RSS - All 50 States')
    print('='*70 + '\n')
    all_cases = []
    for state in STATES:
        print(f'  {state:20}', end='', flush=True)
        cases = scrape_google_news_state(state)
        all_cases.extend(cases)
        print(f' {len(cases)}')
        time.sleep(1)
    return all_cases


# ============================================================
# SOURCE E: CourtListener (v4 API - proper filter queries)
# ============================================================

def scrape_courtlistener():
    print('\n' + '='*70)
    print('SOURCE E: CourtListener - Federal Court Opinions')
    print('='*70 + '\n')
    cases = []
    seen = set()

    queries = [
        ('convicted judge', 'Judicial'),
        ('bribery conviction official', 'Executive'),
        ('corruption public official', 'Executive'),
        ('guilty plea senator', 'Legislative'),
        ('indicted congressman', 'Legislative'),
        ('convicted sheriff', 'Law Enforcement'),
        ('convicted police officer', 'Law Enforcement'),
        ('correctional officer convicted', 'Law Enforcement'),
        ('mayor convicted bribery', 'Executive'),
        ('governor convicted fraud', 'Executive'),
        ('probation officer convicted', 'Law Enforcement'),
        ('state trooper convicted', 'Law Enforcement'),
        ('border patrol agent convicted', 'Law Enforcement'),
        ('federal agent convicted', 'Law Enforcement'),
        ('magistrate judge convicted', 'Judicial'),
        ('school board member convicted', 'Legislative'),
        ('alderman convicted', 'Legislative'),
    ]

    for query, branch_hint in queries:
        print(f'  Searching: {query}')
        try:
            resp = SESSION.get(
                'https://www.courtlistener.com/api/rest/v4/opinions/',
                params={'q': query, 'page_size': 50, 'order_by': '-date_filed', 'type': 'o'},
                timeout=15
            )
            if resp.status_code != 200:
                # Try v3 fallback
                resp = SESSION.get(
                    'https://www.courtlistener.com/api/rest/v3/opinions/',
                    params={'q': query, 'page_size': 50, 'order_by': '-date_filed'},
                    timeout=15
                )
            if resp.status_code != 200:
                continue

            results = resp.json().get('results', [])
            print(f'    {len(results)} results')

            for r in results:
                try:
                    case_name = r.get('case_name', '') or r.get('caseName', '')
                    plain_text = r.get('plain_text', '')[:1500]
                    abs_url = r.get('absolute_url', '')
                    if abs_url and not abs_url.startswith('http'):
                        abs_url = 'https://www.courtlistener.com' + abs_url
                    if not case_name or len(case_name) < 5:
                        continue
                    combined = f"{case_name} {plain_text}".lower()
                    if not contains_any(combined, MISCONDUCT_KEYWORDS):
                        continue
                    fp = make_fingerprint(case_name, abs_url)
                    if fp in seen:
                        continue
                    seen.add(fp)
                    name = 'Unknown Official'
                    if ' v. ' in case_name:
                        parts = case_name.split(' v. ')
                        candidate = parts[0].strip()
                        if 'United States' not in candidate and 'State of' not in candidate and len(candidate) > 2:
                            name = candidate[:100]
                        else:
                            name = parts[1].strip()[:100]
                    else:
                        name = case_name.split(',')[0][:100]

                    case = {
                        'full_name': name,
                        'title': case_name[:200],
                        'position_title': get_position(combined),
                        'official_type': branch_hint,
                        'location': 'Federal',
                        'level': 'Federal',
                        'category': 'Public Official Misconduct',
                        'abuse_of_power_type': get_abuse_type(combined),
                        'case_status': get_status(combined),
                        'date_charged': extract_date(plain_text),
                        'details': plain_text[:2000],
                        'source_url': abs_url,
                        'source_type': 'court_record',
                        'source_date': str(datetime.now().date()),
                        'publication_status': 'draft',
                        'verified_by': 'courtlistener',
                        'verified_at': datetime.now().isoformat(),
                        'fingerprint': fp,
                    }
                    cases.append(case)
                    print(f'      [+] {case_name[:65]}')
                except Exception:
                    continue
        except Exception as e:
            print(f'    Error: {str(e)[:60]}')
        time.sleep(1)

    print(f'  Total from CourtListener: {len(cases)}')
    return cases


# ============================================================
# DEDUPLICATION & UPLOAD
# ============================================================

def dedup(cases):
    seen = {}
    for c in cases:
        fp = c.get('fingerprint', '')
        if fp and fp not in seen:
            seen[fp] = c
    return list(seen.values())


def print_stats(cases, label):
    print(f'\n{"="*70}')
    print(f'{label}: {len(cases)} unique cases')
    branches, levels, statuses, positions = {}, {}, {}, {}
    dates = 0
    for c in cases:
        b = c.get('official_type', 'Unknown')
        branches[b] = branches.get(b, 0) + 1
        lv = c.get('level', 'Unknown')
        levels[lv] = levels.get(lv, 0) + 1
        s = c.get('case_status', 'Unknown')
        statuses[s] = statuses.get(s, 0) + 1
        p = c.get('position_title', 'Unknown')
        positions[p] = positions.get(p, 0) + 1
        if c.get('date_charged'):
            dates += 1

    print('\nBy Branch:')
    for k, v in sorted(branches.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    print('\nBy Level:')
    for k, v in sorted(levels.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    print('\nBy Status:')
    for k, v in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    print('\nTop 15 Positions:')
    for k, v in sorted(positions.items(), key=lambda x: -x[1])[:15]:
        print(f'  {k}: {v}')
    print(f'\nDates found: {dates}/{len(cases)}')


def upload_to_supabase(cases):
    if not cases:
        return 0
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        existing = supabase.table('cases').select('fingerprint').execute()
        existing_fps = {row['fingerprint'] for row in existing.data}
        print(f'\nExisting in DB: {len(existing_fps)}')

        new_cases = [c for c in cases if c.get('fingerprint') not in existing_fps]
        print(f'New cases: {len(new_cases)}  Duplicates skipped: {len(cases) - len(new_cases)}')

        if not new_cases:
            print('All cases already in database.')
            return 0

        uploaded = 0
        for i in range(0, len(new_cases), 50):
            chunk = new_cases[i:i + 50]
            try:
                supabase.table('cases').insert(chunk).execute()
                uploaded += len(chunk)
                print(f'  [+] {uploaded}/{len(new_cases)}')
            except Exception as e:
                print(f'  Error: {str(e)[:80]}')
        return uploaded

    except ImportError:
        print('Supabase not available — saved to JSON only.')
        return 0


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='VeriScope All-Branches Scraper')
    parser.add_argument('--sources', nargs='+',
                        choices=['doj', 'fbi', 'oig', 'news', 'court', 'all'],
                        default=['all'],
                        help='Which sources to run (default: all)')
    parser.add_argument('--output', default='all_branches_cases.json')
    parser.add_argument('--no-upload', action='store_true', help='Skip Supabase upload')
    parser.add_argument('--enrich', action='store_true',
                        help='Run Claude API enrichment after scraping (requires ANTHROPIC_API_KEY)')
    parser.add_argument('--enrich-model', default='claude-haiku-4-5',
                        choices=['claude-haiku-4-5', 'claude-sonnet-4-6', 'claude-opus-4-8'],
                        help='Model to use for enrichment (default: claude-haiku-4-5)')
    parser.add_argument('--enrich-concurrency', type=int, default=5,
                        help='Concurrency for enrichment API calls (default: 5)')
    args = parser.parse_args()

    run_all = 'all' in args.sources
    all_cases = []

    if run_all or 'doj' in args.sources:
        all_cases.extend(scrape_doj_all())

    if run_all or 'fbi' in args.sources:
        all_cases.extend(scrape_fbi_feed())

    if run_all or 'oig' in args.sources:
        all_cases.extend(scrape_all_oig())

    if run_all or 'news' in args.sources:
        all_cases.extend(scrape_google_news_all())

    if run_all or 'court' in args.sources:
        all_cases.extend(scrape_courtlistener())

    all_cases = dedup(all_cases)
    print_stats(all_cases, 'ALL SOURCES COMBINED')

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(all_cases, f, indent=2, default=str)
    print(f'\nSaved: {args.output}')

    # Optional Claude enrichment step
    if args.enrich:
        print(f'\nRunning Claude enrichment (model: {args.enrich_model})...')
        try:
            from claude_enricher import run_enrichment
            enriched_output = args.output.replace('.json', '_enriched.json')
            all_cases = run_enrichment(
                cases=all_cases,
                model=args.enrich_model,
                output_path=enriched_output,
                concurrency=args.enrich_concurrency,
            )
            print(f'Enrichment complete → {enriched_output}')
        except ImportError:
            print('claude_enricher.py not found — skipping enrichment.')
        except Exception as e:
            print(f'Enrichment error: {e} — continuing with unenriched data.')

    uploaded = 0
    if not args.no_upload:
        uploaded = upload_to_supabase(all_cases)

    print(f'\n{"="*70}')
    print(f'ALL-BRANCHES SCRAPER COMPLETE')
    print(f'  Total unique cases found: {len(all_cases)}')
    print(f'  Uploaded to Supabase:     {uploaded}')
    print('='*70 + '\n')
