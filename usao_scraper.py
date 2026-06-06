import argparse, json, logging, time, re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

SEARCH_KEYWORDS = ["sheriff","judge","mayor","police officer","councilman","councilmember","councilwoman","magistrate","commissioner","governor","senator","representative","warden","jailer","correctional officer","correction officer","deputy sheriff","police chief","fire chief","state trooper","district attorney","comptroller","auditor","alderman","constable","prison guard","former officer","former deputy","former detective","former trooper","former prosecutor","former agent"]

MISCONDUCT_KEYWORDS = ["convicted","guilty plea","pleaded guilty","pled guilty","pleads guilty","plead guilty","indicted","grand jury","charged with","charges filed","arrested","sentenced","imprisoned","removed from office","suspended","censured","bribery","extortion","fraud","embezzlement","corruption","money laundering","wire fraud","excessive force","obstruction","perjury","sexual assault","csam","child pornography","child exploitation","child sexual abuse","sex trafficking","civil rights"]

REJECT_KEYWORDS = ["sworn in","appointed","confirmed","nominated","announced candidacy","honors","hometown hero","recognizes","award","weekly","sentenced a","sentences","judge sentences","judge orders","judge hands","federal judge sentences"]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; VeriScope-Research-Bot/1.0)"})
DELAY = 1.0

def get(url, params=None):
    for attempt in range(1, 4):
        try:
            r = SESSION.get(url, params=params, timeout=15)
            if r.status_code == 200: return r
            if r.status_code == 404: return None
            log.warning("HTTP %s attempt %d: %s", r.status_code, attempt, url)
        except Exception as e:
            log.warning("Error %s: %s", url, e)
        time.sleep(DELAY * attempt)
    return None

def search_by_keyword(keyword, page=0, pagesize=50):
    r = get("https://www.justice.gov/api/v1/press_releases.json", {
        "parameters[title]": keyword,
        "pagesize": pagesize,
        "page": page,
        "sort": "date",
        "direction": "DESC"
    })
    if not r: return [], 0
    try:
        data = r.json()
        total = int(data.get("metadata",{}).get("resultset",{}).get("count", 0))
        return data.get("results", []), total
    except Exception as e:
        log.warning("JSON parse error: %s", e)
        return [], 0

def html_to_text(html):
    if not html: return ""
    return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)

def contains_any(text, kws):
    t = text.lower()
    return any(k in t for k in kws)

def is_relevant(title):
    t = title.lower()
    if contains_any(t, REJECT_KEYWORDS): return False
    if not contains_any(t, MISCONDUCT_KEYWORDS): return False
    return True

def get_usao(item):
    comps = item.get("component", [])
    names = [c.get("name","") if isinstance(c, dict) else str(c) for c in comps]
    usaos = [n for n in names if n.startswith("USAO -")]
    return usaos[0] if usaos else None

def parse_date(s):
    if not s: return None
    if str(s).lstrip("-").isdigit(): return datetime.utcfromtimestamp(int(s)).strftime("%Y-%m-%d")
    for fmt in ["%B %d, %Y","%b %d, %Y","%m/%d/%Y","%Y-%m-%d"]:
        try: return datetime.strptime(str(s).strip(), fmt).strftime("%Y-%m-%d")
        except: pass
    return None

def extract_location(text):
    m = re.match(r"^([A-Z][A-Za-z .]+(?:,\s*[A-Z]{2})?)\s*[-]", text.strip())
    return m.group(1).strip() if m else "Unknown"

def case_status(t, b):
    c = f"{t} {b}".lower()
    if any(k in c for k in ["acquitted","not guilty"]): return "Acquitted"
    if any(k in c for k in ["convicted","found guilty","guilty verdict"]): return "Convicted"
    if any(k in c for k in ["sentenced","sentencing"]): return "Sentenced"
    if any(k in c for k in ["pleaded guilty","pled guilty","guilty plea","plead guilty","pleads guilty"]): return "Convicted"
    if any(k in c for k in ["indicted","grand jury"]): return "Indicted"
    if any(k in c for k in ["charged with","charges filed","arrested"]): return "Charges Filed"
    if any(k in c for k in ["dismissed","charges dropped"]): return "Dismissed"
    return "Under Investigation"

def official_type(t, b):
    c = f"{t} {b}".lower()
    if any(k in c for k in ["judge","magistrate","clerk of court"]): return "Judicial"
    if any(k in c for k in ["police","sheriff","deputy","trooper","correctional","jailer","warden","customs","border patrol","detective","correction officer","prison guard"]): return "Law Enforcement"
    if any(k in c for k in ["senator","representative","congressman","congresswoman","governor","mayor","city council","councilman","councilmember","councilwoman","alderman"]): return "Legislative"
    return "Executive"

def abuse_type(t, b):
    c = f"{t} {b}".lower()
    if any(k in c for k in ["csam","child pornography","child exploitation","child sexual abuse","sex trafficking of a minor"]): return "CSAM"
    if any(k in c for k in ["bribery","kickback","extortion"]): return "Bribery/Extortion"
    if any(k in c for k in ["fraud","embezzlement","theft","wire fraud","mail fraud"]): return "Fraud/Embezzlement"
    if any(k in c for k in ["civil rights","excessive force","deprivation of rights"]): return "Civil Rights Violation"
    if any(k in c for k in ["drug","narcotics","trafficking","fentanyl","cocaine","methamphetamine"]): return "Drug Trafficking"
    if any(k in c for k in ["obstruction","perjury","false statement"]): return "Obstruction/Perjury"
    if any(k in c for k in ["sexual assault","rape","sex offense","sexual misconduct"]): return "Sexual Misconduct"
    return "Corruption"

def to_case(item):
    title = item.get("title","")
    body = html_to_text(item.get("body",""))
    url = item.get("url","")
    if url and not url.startswith("http"):
        url = "https://www.justice.gov" + url
    usao = get_usao(item) or ""
    return {
        "full_name": "",
        "title": title,
        "position_title": "",
        "official_type": official_type(title, body),
        "agency_or_office": usao,
        "location": extract_location(body),
        "level": "Federal",
        "category": "Public Official Misconduct",
        "abuse_of_power_type": abuse_type(title, body),
        "specific_charges": "",
        "case_status": case_status(title, body),
        "date_charged": parse_date(item.get("date","")),
        "date_resolved": None,
        "details": body[:2000],
        "source_url": url,
        "source_type": "official_report",
        "publication_status": "draft",
        "verified_by": "bulk_import",
        "verified_at": datetime.utcnow().isoformat() + "Z"
    }

def scrape_all(max_pages=20):
    all_cases = []
    seen = set()
    for kw in SEARCH_KEYWORDS:
        log.info("Searching: %s", kw)
        for page in range(max_pages):
            results, total = search_by_keyword(kw, page=page, pagesize=50)
            if not results: break
            log.info("  page %d: %d results (total: %d)", page, len(results), total)
            new_this_page = 0
            for item in results:
                url = item.get("url","")
                if url in seen: continue
                title = item.get("title","")
                if not get_usao(item): continue
                if not is_relevant(title): continue
                seen.add(url)
                all_cases.append(to_case(item))
                new_this_page += 1
                log.info("  + %s", title[:80])
            time.sleep(DELAY)
            if len(results) < 50: break
        log.info("Running total: %d", len(all_cases))
    return all_cases

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="cases.json")
    p.add_argument("--max-pages", type=int, default=20)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()
    if args.verbose: logging.getLogger().setLevel(logging.DEBUG)
    log.info("Starting VeriScope USAO scraper")
    cases = scrape_all(args.max_pages)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, default=str)
    log.info("Saved %d cases to %s", len(cases), args.output)

if __name__ == "__main__":
    main()
