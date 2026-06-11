"""
VeriScope Production Pipeline v2.0
Justice.gov API + Batch Upsert + Comprehensive Logging
"""

import os
import sys
import requests
import json
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

SUPABASE_URL = "https://sqaibfaniwbixviptilx.supabase.co"
SUPABASE_KEY = "sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ"

DOJ_API = "https://www.justice.gov/api/v1/press_releases.json"

OFFICIAL_KEYWORDS = [
    'judge', 'senator', 'representative', 'governor', 'mayor', 'sheriff',
    'police', 'chief', 'prosecutor', 'attorney general', 'commissioner',
    'magistrate', 'auditor', 'fire', 'fbi', 'dea', 'agent', 'officer',
    'director', 'clerk', 'treasurer', 'assessor', 'constable'
]

MISCONDUCT_KEYWORDS = [
    'convicted', 'guilty', 'indicted', 'charged', 'arrested', 'sentenced',
    'plea', 'corruption', 'bribery', 'fraud', 'embezzlement', 'abuse',
    'removed', 'suspended', 'resigned', 'dismissed'
]

REJECT_KEYWORDS = [
    'sworn in', 'appointed', 'confirmed', 'announced', 'nominated',
    'elected', 'hired', 'promoted', 'released statement'
]

USAO_TO_STATE = {
    'usao-al': 'Alabama', 'usao-ak': 'Alaska', 'usao-az': 'Arizona',
    'usao-ar': 'Arkansas', 'usao-cd': 'California', 'usao-ed': 'California',
    'usao-nd': 'California', 'usao-sd': 'California', 'usao-co': 'Colorado',
    'usao-ct': 'Connecticut', 'usao-de': 'Delaware', 'usao-fl': 'Florida',
    'usao-md': 'Florida', 'usao-sd': 'Florida', 'usao-ga': 'Georgia',
    'usao-hi': 'Hawaii', 'usao-id': 'Idaho', 'usao-cd': 'Illinois',
    'usao-ed': 'Illinois', 'usao-nd': 'Illinois', 'usao-sd': 'Illinois',
    'usao-in': 'Indiana', 'usao-nd': 'Indiana', 'usao-sd': 'Indiana',
    'usao-ia': 'Iowa', 'usao-nd': 'Iowa', 'usao-sd': 'Iowa',
    'usao-ks': 'Kansas', 'usao-ky': 'Kentucky', 'usao-ed': 'Kentucky',
    'usao-wd': 'Kentucky', 'usao-la': 'Louisiana', 'usao-ed': 'Louisiana',
    'usao-md': 'Louisiana', 'usao-wd': 'Louisiana', 'usao-me': 'Maine',
    'usao-md': 'Maryland', 'usao-ma': 'Massachusetts', 'usao-ed': 'Massachusetts',
    'usao-wd': 'Massachusetts', 'usao-ed': 'Michigan', 'usao-wd': 'Michigan',
    'usao-d': 'Minnesota', 'usao-ed': 'Minnesota', 'usao-wd': 'Minnesota',
    'usao-nd': 'Mississippi', 'usao-sd': 'Mississippi', 'usao-ed': 'Missouri',
    'usao-wd': 'Missouri', 'usao-d': 'Montana', 'usao-ne': 'Nebraska',
    'usao-d': 'Nevada', 'usao-nh': 'New Hampshire', 'usao-d': 'New Jersey',
    'usao-nm': 'New Mexico', 'usao-ed': 'New York', 'usao-nd': 'New York',
    'usao-sd': 'New York', 'usao-wd': 'New York', 'usao-ed': 'North Carolina',
    'usao-md': 'North Carolina', 'usao-wd': 'North Carolina', 'usao-d': 'North Dakota',
    'usao-nd': 'North Dakota', 'usao-sd': 'North Dakota', 'usao-nd': 'Ohio',
    'usao-sd': 'Ohio', 'usao-wd': 'Ohio', 'usao-ed': 'Oklahoma',
    'usao-nd': 'Oklahoma', 'usao-wd': 'Oklahoma', 'usao-d': 'Oregon',
    'usao-ed': 'Pennsylvania', 'usao-md': 'Pennsylvania', 'usao-wd': 'Pennsylvania',
    'usao-ri': 'Rhode Island', 'usao-d': 'South Carolina', 'usao-sd': 'South Carolina',
    'usao-d': 'South Dakota', 'usao-ed': 'Tennessee', 'usao-md': 'Tennessee',
    'usao-wd': 'Tennessee', 'usao-ed': 'Texas', 'usao-nd': 'Texas',
    'usao-sd': 'Texas', 'usao-wd': 'Texas', 'usao-d': 'Utah',
    'usao-vt': 'Vermont', 'usao-ed': 'Virginia', 'usao-wd': 'Virginia',
    'usao-ed': 'Washington', 'usao-wd': 'Washington', 'usao-nd': 'West Virginia',
    'usao-sd': 'West Virginia', 'usao-ed': 'Wisconsin', 'usao-wd': 'Wisconsin',
    'usao-d': 'Wyoming'
}

# ============================================================================
# LOGGING
# ============================================================================

class Logger:
    def __init__(self):
        self.logs = []
    
    def _log(self, level, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {msg}"
        print(formatted)
        self.logs.append(formatted)
    
    def info(self, msg):
        self._log("INFO", msg)
    
    def success(self, msg):
        self._log("OK", msg)
    
    def error(self, msg):
        self._log("ERROR", msg)
    
    def warning(self, msg):
        self._log("WARN", msg)

logger = Logger()

# ============================================================================
# SCRAPER
# ============================================================================

def scrape_justice_gov(pages: int = 5) -> List[Dict]:
    """Scrape DOJ press releases from justice.gov API"""
    logger.info("Starting DOJ API scrape...")
    
    cases = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'VeriScope/1.0'})
    
    search_terms = [
        'convicted judge', 'indicted official', 'charged mayor',
        'sentenced sheriff', 'corruption', 'bribery', 'fraud'
    ]
    
    for term in search_terms:
        for page in range(pages):
            try:
                logger.info(f"  Fetching page {page + 1} for: {term}")
                
                params = {
                    'parameters[title]': term,
                    'page': page,
                    'pagesize': 50
                }
                
                response = session.get(DOJ_API, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                if not data.get('results'):
                    logger.warning(f"  No results for page {page}")
                    break
                
                for item in data['results']:
                    case_data = {
                        'title': item.get('title', ''),
                        'details': item.get('body', '')[:3000],
                        'source_url': item.get('url', ''),
                        'source_date': item.get('posted', '')[:10],
                        'location': extract_location_from_url(item.get('url', '')),
                    }
                    
                    if case_data['title'] and case_data['source_url']:
                        cases.append(case_data)
                
                logger.success(f"  Retrieved {len(data['results'])} items")
                
            except Exception as e:
                logger.error(f"  Error on page {page}: {str(e)}")
                continue
    
    logger.success(f"Scraped {len(cases)} raw cases")
    return cases

# ============================================================================
# VALIDATION
# ============================================================================

def is_valid_case(case: Dict) -> bool:
    """Check if case meets validation criteria"""
    text = f"{case.get('title', '')} {case.get('details', '')}".lower()
    
    # Check reject keywords
    if any(kw in text for kw in REJECT_KEYWORDS):
        return False
    
    # Check official keywords
    has_official = any(kw in text for kw in OFFICIAL_KEYWORDS)
    
    # Check misconduct keywords
    has_misconduct = any(kw in text for kw in MISCONDUCT_KEYWORDS)
    
    return has_official and has_misconduct

def validate_cases(cases: List[Dict]) -> tuple:
    """Validate cases against criteria"""
    logger.info(f"Validating {len(cases)} cases...")
    
    valid = []
    rejected = 0
    
    for case in cases:
        if is_valid_case(case):
            valid.append(case)
        else:
            rejected += 1
    
    logger.success(f"Valid: {len(valid)}, Rejected: {rejected}")
    return valid, rejected

# ============================================================================
# ENRICHMENT
# ============================================================================

def extract_location_from_url(url: str) -> str:
    """Extract state from USAO URL pattern"""
    for pattern, state in USAO_TO_STATE.items():
        if pattern in url.lower():
            return state
    return "Unknown"

def extract_name(text: str) -> str:
    """Extract official name from text"""
    match = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', text)
    if match:
        return match.group(1)
    return "Unknown Official"

def extract_position(text: str) -> str:
    """Extract position title"""
    text_lower = text.lower()
    
    if 'judge' in text_lower:
        return 'Judge'
    elif 'senator' in text_lower:
        return 'Senator'
    elif 'representative' in text_lower or 'congressman' in text_lower:
        return 'Representative'
    elif 'mayor' in text_lower:
        return 'Mayor'
    elif 'sheriff' in text_lower:
        return 'Sheriff'
    elif 'police' in text_lower:
        return 'Police Officer'
    elif 'prosecutor' in text_lower or 'attorney' in text_lower:
        return 'Prosecutor'
    elif 'governor' in text_lower:
        return 'Governor'
    
    return 'Public Official'

def extract_case_status(text: str) -> str:
    """Extract case status from text"""
    text_lower = text.lower()
    
    if 'convicted' in text_lower or 'guilty plea' in text_lower:
        return 'Convicted'
    elif 'indicted' in text_lower:
        return 'Indicted'
    elif 'sentenced' in text_lower:
        return 'Sentenced'
    elif 'charged' in text_lower:
        return 'Charged'
    elif 'acquitted' in text_lower:
        return 'Acquitted'
    
    return 'Charged'

def extract_category(text: str) -> str:
    """Extract misconduct category"""
    text_lower = text.lower()
    
    if 'sexual' in text_lower or 'csam' in text_lower or 'child' in text_lower:
        return 'Sexual Abuse'
    elif 'corruption' in text_lower or 'bribery' in text_lower:
        return 'Corruption'
    elif 'fraud' in text_lower or 'embezzlement' in text_lower:
        return 'Financial Crime'
    elif 'assault' in text_lower:
        return 'Assault'
    elif 'dui' in text_lower or 'drunk' in text_lower:
        return 'DUI/Substance Abuse'
    
    return 'Misconduct'

def enrich_case(case: Dict) -> Dict:
    """Enrich case with extracted data"""
    text = f"{case.get('title', '')} {case.get('details', '')}"
    
    enriched = {
        'full_name': extract_name(text),
        'title': case.get('title', '')[:500],
        'position_title': extract_position(text),
        'case_status': extract_case_status(text),
        'category': extract_category(text),
        'location': case.get('location', 'Unknown'),
        'level': 'Federal',
        'official_type': 'Judicial' if 'judge' in text.lower() else 'Executive',
        'details': case.get('details', '')[:2000],
        'source_url': case.get('source_url', ''),
        'source_date': case.get('source_date', datetime.now().strftime('%Y-%m-%d')),
        'source_type': 'court_record',
        'publication_status': 'draft',
        'verified_by': 'bulk_import',
        'verified_at': datetime.now().isoformat(),
    }
    
    # Generate fingerprint
    fp_text = f"{enriched['full_name']}{enriched['position_title']}{enriched['source_url']}"
    enriched['fingerprint'] = hashlib.md5(fp_text.encode()).hexdigest()
    
    return enriched

# ============================================================================
# DEDUPLICATION
# ============================================================================

def deduplicate_cases(cases: List[Dict]) -> List[Dict]:
    """Remove duplicate cases"""
    logger.info(f"Deduplicating {len(cases)} cases...")
    
    seen = set()
    unique = []
    
    for case in cases:
        fp = case.get('fingerprint', '')
        if fp and fp not in seen:
            seen.add(fp)
            unique.append(case)
    
    logger.success(f"Unique: {len(unique)}, Removed: {len(cases) - len(unique)}")
    return unique

# ============================================================================
# SUPABASE UPLOAD
# ============================================================================

def upload_to_supabase(cases: List[Dict], dry_run: bool = True) -> Dict:
    """Upload cases to Supabase in batches"""
    logger.info(f"Connecting to Supabase...")
    
    try:
        from supabase import create_client
    except ImportError:
        logger.error("supabase-py not installed. Run: pip install supabase")
        return {'success': 0, 'errors': 0, 'total': 0}
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.success("Connected to Supabase")
    except Exception as e:
        logger.error(f"Failed to connect: {str(e)}")
        return {'success': 0, 'errors': 0, 'total': 0}
    
    if dry_run:
        logger.warning("DRY-RUN MODE: No uploads")
        logger.info(f"Would upload {len(cases)} cases")
        return {'success': len(cases), 'errors': 0, 'total': len(cases), 'dry_run': True}
    
    logger.info(f"Uploading {len(cases)} cases in batches of 50...")
    
    success = 0
    errors = 0
    
    for i in range(0, len(cases), 50):
        batch = cases[i:i+50]
        batch_num = (i // 50) + 1
        
        try:
            response = supabase.table('cases').upsert(batch, on_conflict='fingerprint').execute()
            success += len(batch)
            progress = min(100, 100 * (i + 50) // len(cases))
            logger.success(f"Batch {batch_num}: Uploaded {len(batch)} ({progress}%)")
        except Exception as e:
            errors += len(batch)
            logger.error(f"Batch {batch_num} failed: {str(e)}")
    
    return {'success': success, 'errors': errors, 'total': len(cases)}

# ============================================================================
# STATISTICS
# ============================================================================

def get_statistics(cases: List[Dict]) -> Dict:
    """Generate statistics"""
    logger.info("Generating statistics...")
    
    stats = {
        'total_cases': len(cases),
        'by_location': {},
        'by_position': {},
        'by_status': {},
        'by_category': {},
    }
    
    for case in cases:
        loc = case.get('location', 'Unknown')
        stats['by_location'][loc] = stats['by_location'].get(loc, 0) + 1
        
        pos = case.get('position_title', 'Unknown')
        stats['by_position'][pos] = stats['by_position'].get(pos, 0) + 1
        
        status = case.get('case_status', 'Unknown')
        stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        cat = case.get('category', 'Unknown')
        stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
    
    return stats

# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("="*70)
    logger.info("VeriScope Production Pipeline v2.0")
    logger.info("="*70)
    
    upload_flag = "--upload" in sys.argv
    
    if not upload_flag:
        logger.warning("DRY-RUN MODE (no uploads)")
        logger.info("Use: python run_final_v2.py --upload")
    else:
        logger.success("Upload mode ENABLED")
    
    logger.info("\n[STEP 1/5] SCRAPING")
    logger.info("="*70)
    raw_cases = scrape_justice_gov(pages=3)
    
    if not raw_cases:
        logger.error("No cases scraped. Exiting.")
        return
    
    logger.info("\n[STEP 2/5] VALIDATION")
    logger.info("="*70)
    valid_cases, rejected = validate_cases(raw_cases)
    
    if not valid_cases:
        logger.error("No valid cases. Exiting.")
        return
    
    logger.info("\n[STEP 3/5] ENRICHMENT")
    logger.info("="*70)
    logger.info("Extracting names, positions, statuses...")
    enriched_cases = [enrich_case(c) for c in valid_cases]
    logger.success(f"Enriched {len(enriched_cases)} cases")
    
    logger.info("\n[STEP 4/5] DEDUPLICATION")
    logger.info("="*70)
    final_cases = deduplicate_cases(enriched_cases)
    
    logger.info("\n[STEP 5/5] UPLOAD")
    logger.info("="*70)
    upload_result = upload_to_supabase(final_cases, dry_run=not upload_flag)
    
    logger.info("\n[STATISTICS]")
    logger.info("="*70)
    stats = get_statistics(final_cases)
    logger.info(f"Total: {stats['total_cases']}")
    logger.info(f"Locations: {len(stats['by_location'])}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(f'cases_{timestamp}.json', 'w') as f:
        json.dump(final_cases, f, indent=2)
    logger.success(f"Saved: cases_{timestamp}.json")
    
    with open(f'pipeline_report_{timestamp}.json', 'w') as f:
        report = {
            'timestamp': timestamp,
            'scraped': len(raw_cases),
            'validated': len(valid_cases),
            'rejected': rejected,
            'deduplicated': len(final_cases),
            'upload_success': upload_result['success'],
            'upload_errors': upload_result['errors'],
            'statistics': stats,
            'logs': logger.logs
        }
        json.dump(report, f, indent=2)
    logger.success(f"Saved: pipeline_report_{timestamp}.json")
    
    logger.info("\n" + "="*70)
    logger.success("PIPELINE COMPLETE!")
    logger.info("="*70)

if __name__ == '__main__':
    main()
