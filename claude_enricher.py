#!/usr/bin/env python3
"""
VeriScope Claude Enrichment Step
Reads scraped case records and uses Claude API to accurately extract:
  - defendant name (full_name, first_name, last_name)
  - position/role (position_title)
  - branch of government (official_type)
  - jurisdiction level (level) and state (location)
  - employer (agency_or_office)
  - specific charges
  - misconduct category (abuse_of_power_type)
  - plain-English summary (ai_summary)

Usage:
  python claude_enricher.py                            # reads validated_cases.json
  python claude_enricher.py --dry-run                  # first 5 cases, no file output
  python claude_enricher.py --input all_branches_cases.json
  python claude_enricher.py --model claude-sonnet-4-6 --concurrency 15
  python claude_enricher.py --upload                   # also upsert to Supabase
  python claude_enricher.py --force                    # re-enrich already-done records
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

import anthropic
from bs4 import BeautifulSoup

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://sqaibfaniwbixviptilx.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ')

DEFAULT_MODEL = 'claude-haiku-4-5'
DEFAULT_CONCURRENCY = 5

# ============================================================
# SYSTEM PROMPT (stable — eligible for prompt caching)
# ============================================================

SYSTEM_PROMPT = """\
You are a legal data extraction specialist analyzing U.S. Department of Justice, FBI, \
and Inspector General press releases about public official misconduct.

Your task: extract structured information about the DEFENDANT — the public official \
who is being charged, convicted, or sentenced for wrongdoing.

Critical rules:
1. The DEFENDANT is the person ACCUSED of a crime, NOT the judge, prosecutor, victim, or witness.
2. Press release titles usually name the defendant:
   "Former Florida Corrections Officer Convicted of Bribery" → officer is the defendant.
3. If the title says "Man charged with threatening a judge/detective/officer", the official \
is likely the VICTIM — read the body to find the actual defendant.
4. For "Seven Defendants Convicted" with multiple people, extract the FIRST named defendant.
5. Always use information explicitly stated in the text — never infer or fabricate.
6. For location: use the state name (e.g. "Florida"), not city names. \
Use "Federal" only if truly no state can be determined.
7. The defendant's position is what they held AT THE TIME OF THE OFFENSE, \
not "defendant" or "inmate"."""

# ============================================================
# CLAUDE TOOL SCHEMA
# ============================================================

EXTRACTION_TOOL = {
    'name': 'extract_case_info',
    'description': (
        'Extract structured information about the charged/convicted public official '
        'from a government press release. Focus ONLY on the defendant.'
    ),
    'input_schema': {
        'type': 'object',
        'required': [
            'full_name', 'first_name', 'last_name', 'position_title',
            'official_type', 'level', 'location', 'agency_or_office',
            'specific_charges', 'abuse_of_power_type', 'ai_summary',
        ],
        'properties': {
            'full_name': {
                'type': 'string',
                'description': (
                    "Full legal name of the DEFENDANT (the official being charged/convicted). "
                    "Examples: 'Paul Tillis', 'Maria Elena Rodriguez', 'James R. Brown III'. "
                    "Use 'Unknown' only if genuinely absent from the text."
                ),
            },
            'first_name': {
                'type': 'string',
                'description': "Defendant's first name. Use 'Unknown' if not found.",
            },
            'last_name': {
                'type': 'string',
                'description': "Defendant's last name. Use 'Unknown' if not found.",
            },
            'position_title': {
                'type': 'string',
                'description': (
                    "Defendant's official role/position at time of offense. "
                    "Examples: 'Corrections Officer', 'State Senator', 'Deputy Sheriff', "
                    "'Police Detective', 'County Commissioner', 'Immigration Judge'. "
                    "Do NOT use 'defendant', 'inmate', or the judge's title."
                ),
            },
            'official_type': {
                'type': 'string',
                'enum': ['Judicial', 'Legislative', 'Executive', 'Law Enforcement'],
                'description': (
                    "Branch/category of government the defendant belongs to. "
                    "Judicial = judges, magistrates, court officials. "
                    "Legislative = senators, representatives, council members, school boards. "
                    "Law Enforcement = police, sheriffs, corrections, federal agents (FBI/DEA/ATF/ICE). "
                    "Executive = governors, mayors, agency directors, other officials."
                ),
            },
            'level': {
                'type': 'string',
                'enum': ['Federal', 'State', 'County', 'City'],
                'description': (
                    "Jurisdiction level of the defendant's position. "
                    "Federal = FBI/DEA/ATF/ICE agents, U.S. marshals, federal officials. "
                    "State = state police, state legislators, state agency officials. "
                    "County = county sheriff, county commissioner, county judge. "
                    "City = city council, municipal police, city officials."
                ),
            },
            'location': {
                'type': 'string',
                'description': (
                    "State where the crime occurred or defendant's jurisdiction. "
                    "Use full state name: 'Florida', 'California', 'Texas'. "
                    "For D.C.-based officials use 'District of Columbia'. "
                    "Use 'Federal' only if no state can be determined."
                ),
            },
            'agency_or_office': {
                'type': 'string',
                'description': (
                    "Name of defendant's employer agency or government office. "
                    "Examples: 'Florida Department of Corrections', "
                    "'San Diego County Sheriff's Office', 'Chicago Police Department', "
                    "'U.S. Customs and Border Protection'. Use empty string if not found."
                ),
            },
            'specific_charges': {
                'type': 'string',
                'description': (
                    "Comma-separated list of the specific charges or offenses from the text. "
                    "Examples: 'bribery, wire fraud', "
                    "'deprivation of rights under color of law, use of firearm', "
                    "'production of child sexual abuse material, distribution of CSAM'. "
                    "Use the actual charge names as written in the press release."
                ),
            },
            'abuse_of_power_type': {
                'type': 'string',
                'enum': [
                    'Bribery/Extortion',
                    'Fraud/Embezzlement',
                    'Civil Rights Violation',
                    'Drug Trafficking',
                    'CSAM/Child Exploitation',
                    'Sexual Misconduct',
                    'Obstruction/Perjury',
                    'Corruption',
                ],
                'description': (
                    "Primary category of misconduct — pick the most specific match. "
                    "Civil Rights Violation covers excessive force, deprivation of rights. "
                    "Corruption is the catch-all for other abuse of office."
                ),
            },
            'ai_summary': {
                'type': 'string',
                'description': (
                    "1-2 sentence plain English summary: who the official is, "
                    "what they did, and the outcome. "
                    "Example: 'John Smith, a former San Diego County sheriff's deputy, "
                    "was sentenced to 10 years in federal prison for fatally shooting "
                    "an unarmed man as he fled. He was convicted of civil rights violations.'"
                ),
            },
        },
        'additionalProperties': False,
    },
}

# ============================================================
# HELPERS
# ============================================================

def strip_html(raw: str) -> str:
    if not raw:
        return ''
    text = BeautifulSoup(raw, 'lxml').get_text(separator=' ', strip=True)
    return re.sub(r'\s+', ' ', text).strip()


def build_user_message(case: dict) -> str:
    clean = strip_html(case.get('details', ''))
    agency = case.get('agency_or_office', '')
    return (
        f"Title: {case.get('title', '')}\n\n"
        f"Agency/Source: {agency}\n\n"
        f"Press release text:\n{clean[:3500]}"
    )


def merge_enriched(original: dict, extracted: dict) -> dict:
    enriched = dict(original)
    enriched.update({
        'full_name':           extracted.get('full_name', original.get('full_name', '')),
        'first_name':          extracted.get('first_name', ''),
        'last_name':           extracted.get('last_name', ''),
        'position_title':      extracted.get('position_title', original.get('position_title', '')),
        'official_type':       extracted.get('official_type', original.get('official_type', '')),
        'level':               extracted.get('level', original.get('level', '')),
        'location':            extracted.get('location', original.get('location', '')),
        'agency_or_office':    extracted.get('agency_or_office', original.get('agency_or_office', '')),
        'specific_charges':    extracted.get('specific_charges', ''),
        'abuse_of_power_type': extracted.get('abuse_of_power_type', original.get('abuse_of_power_type', '')),
        'ai_summary':          extracted.get('ai_summary', ''),
        'details':             strip_html(original.get('details', '')),
        'verified_by':         'claude_enricher',
        'verified_at':         datetime.now(timezone.utc).isoformat(),
    })
    return enriched


# ============================================================
# ASYNC ENRICHMENT
# ============================================================

async def enrich_one(case: dict, model: str, semaphore: asyncio.Semaphore,
                     async_client: anthropic.AsyncAnthropic, log: logging.Logger) -> dict:
    async with semaphore:
        fp = case.get('fingerprint', '')[:8]
        try:
            response = await async_client.messages.create(
                model=model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=[EXTRACTION_TOOL],
                tool_choice={'type': 'tool', 'name': 'extract_case_info'},
                messages=[{'role': 'user', 'content': build_user_message(case)}],
            )
            tool_block = next(
                (b for b in response.content if b.type == 'tool_use'), None
            )
            if not tool_block:
                log.warning('[%s] No tool_use block in response — keeping original', fp)
                return case
            return merge_enriched(case, tool_block.input)

        except anthropic.RateLimitError as e:
            retry_after = 30
            try:
                retry_after = int(e.response.headers.get('retry-after', 30))
            except Exception:
                pass
            log.warning('[%s] Rate limited — sleeping %ds', fp, retry_after)
            await asyncio.sleep(retry_after)
            # one retry
            try:
                response = await async_client.messages.create(
                    model=model,
                    max_tokens=1024,
                    system=SYSTEM_PROMPT,
                    tools=[EXTRACTION_TOOL],
                    tool_choice={'type': 'tool', 'name': 'extract_case_info'},
                    messages=[{'role': 'user', 'content': build_user_message(case)}],
                )
                tool_block = next(
                    (b for b in response.content if b.type == 'tool_use'), None
                )
                if tool_block:
                    return merge_enriched(case, tool_block.input)
            except Exception as e2:
                log.warning('[%s] Retry failed: %s', fp, e2)
            return case

        except Exception as e:
            log.warning('[%s] Enrichment failed: %s', fp, str(e)[:120])
            return case


async def enrich_all_async(cases: list, model: str, concurrency: int,
                           log: logging.Logger) -> list:
    async_client = anthropic.AsyncAnthropic()
    semaphore = asyncio.Semaphore(concurrency)
    total = len(cases)
    results = []

    tasks = [enrich_one(c, model, semaphore, async_client, log) for c in cases]

    chunk_size = 50
    for i in range(0, total, chunk_size):
        chunk_tasks = tasks[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk_tasks)
        results.extend(chunk_results)
        done = min(i + chunk_size, total)
        log.info('Progress: %d / %d enriched', done, total)

    return results


# ============================================================
# SUPABASE UPSERT
# ============================================================

DB_FIELDS = {
    'full_name', 'first_name', 'last_name', 'title', 'position_title',
    'official_type', 'level', 'location', 'agency_or_office',
    'category', 'abuse_of_power_type', 'specific_charges', 'case_status',
    'date_charged', 'details', 'source_url', 'source_type', 'source_date',
    'publication_status', 'verified_by', 'verified_at', 'fingerprint',
    'ai_summary',
}


def upsert_to_supabase(cases: list, log: logging.Logger) -> int:
    try:
        from supabase import create_client
    except ImportError:
        log.error('supabase package not installed — skipping upload')
        return 0

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    updated = 0
    errors = 0

    for i in range(0, len(cases), 50):
        chunk = cases[i:i + 50]
        records = [{k: v for k, v in c.items() if k in DB_FIELDS} for c in chunk]
        try:
            supabase.table('cases').upsert(records, on_conflict='fingerprint').execute()
            updated += len(chunk)
            log.info('Upserted %d / %d', updated, len(cases))
        except Exception as e:
            log.warning('Supabase upsert error: %s', str(e)[:120])
            errors += len(chunk)

    log.info('Supabase done: %d updated, %d errors', updated, errors)
    return updated


# ============================================================
# PUBLIC ENTRY POINT (importable)
# ============================================================

def run_enrichment(
    cases: list,
    model: str = DEFAULT_MODEL,
    output_path: str = 'enriched_cases.json',
    concurrency: int = DEFAULT_CONCURRENCY,
    force: bool = False,
    upload: bool = False,
    log: logging.Logger | None = None,
) -> list:
    if log is None:
        log = logging.getLogger('claude_enricher')

    to_enrich = cases if force else [
        c for c in cases if c.get('verified_by') != 'claude_enricher'
    ]
    already_done = [] if force else [
        c for c in cases if c.get('verified_by') == 'claude_enricher'
    ]

    log.info('Cases to enrich: %d  |  Already done: %d  |  Model: %s  |  Concurrency: %d',
             len(to_enrich), len(already_done), model, concurrency)

    if to_enrich:
        enriched_new = asyncio.run(enrich_all_async(to_enrich, model, concurrency, log))
    else:
        enriched_new = []

    all_enriched = already_done + enriched_new

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_enriched, f, indent=2, default=str)
        log.info('Saved %d cases → %s', len(all_enriched), output_path)

    if upload:
        upsert_to_supabase(all_enriched, log)

    return all_enriched


# ============================================================
# CLI
# ============================================================

def print_stats(cases: list) -> None:
    branches, levels, statuses, unknown_names = {}, {}, {}, 0
    filled_charges, filled_agency, filled_summary = 0, 0, 0

    for c in cases:
        b = c.get('official_type', 'Unknown')
        branches[b] = branches.get(b, 0) + 1
        lv = c.get('level', 'Unknown')
        levels[lv] = levels.get(lv, 0) + 1
        if c.get('full_name', '').lower() in ('unknown', 'unknown official', ''):
            unknown_names += 1
        if c.get('specific_charges', '').strip():
            filled_charges += 1
        if c.get('agency_or_office', '').strip():
            filled_agency += 1
        if c.get('ai_summary', '').strip():
            filled_summary += 1

    n = len(cases)
    print(f'\n{"="*65}')
    print(f'Enrichment results: {n} cases')
    print(f'  Unknown names remaining: {unknown_names} ({100*unknown_names//max(n,1)}%)')
    print(f'  Specific charges filled: {filled_charges} ({100*filled_charges//max(n,1)}%)')
    print(f'  Agency filled:           {filled_agency} ({100*filled_agency//max(n,1)}%)')
    print(f'  AI summary filled:       {filled_summary} ({100*filled_summary//max(n,1)}%)')
    print('\nBy Branch:')
    for k, v in sorted(branches.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    print('\nBy Level:')
    for k, v in sorted(levels.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}')
    print('='*65 + '\n')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Claude API enrichment for VeriScope case records',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--input', default='validated_cases.json',
                        help='Input JSON file (default: validated_cases.json)')
    parser.add_argument('--output', default='enriched_cases.json',
                        help='Output JSON file (default: enriched_cases.json)')
    parser.add_argument('--model', default=DEFAULT_MODEL,
                        choices=['claude-haiku-4-5', 'claude-haiku-4-5-20251001',
                                 'claude-sonnet-4-6', 'claude-opus-4-8'],
                        help=f'Claude model (default: {DEFAULT_MODEL})')
    parser.add_argument('--concurrency', type=int, default=DEFAULT_CONCURRENCY,
                        help=f'Max concurrent API calls (default: {DEFAULT_CONCURRENCY})')
    parser.add_argument('--force', action='store_true',
                        help='Re-enrich even records already marked claude_enricher')
    parser.add_argument('--upload', action='store_true',
                        help='Upsert enriched records to Supabase')
    parser.add_argument('--dry-run', action='store_true',
                        help='Process first 5 cases only, print results, no file written')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )
    log = logging.getLogger('claude_enricher')

    if not os.getenv('ANTHROPIC_API_KEY'):
        log.error('ANTHROPIC_API_KEY environment variable not set.')
        sys.exit(1)

    if not os.path.exists(args.input):
        log.error('Input file not found: %s', args.input)
        sys.exit(1)

    with open(args.input, encoding='utf-8') as f:
        cases = json.load(f)
    log.info('Loaded %d cases from %s', len(cases), args.input)

    if args.dry_run:
        log.info('DRY RUN — processing first 5 cases only')
        sample = cases[:5]
        enriched = asyncio.run(enrich_all_async(sample, args.model, 2, log))
        for i, c in enumerate(enriched, 1):
            print(f'\n--- Case {i} ---')
            print(f'  Title:          {c.get("title","")[:80]}')
            print(f'  full_name:      {c.get("full_name","")}')
            print(f'  position_title: {c.get("position_title","")}')
            print(f'  official_type:  {c.get("official_type","")}')
            print(f'  level:          {c.get("level","")}')
            print(f'  location:       {c.get("location","")}')
            print(f'  agency:         {c.get("agency_or_office","")}')
            print(f'  charges:        {c.get("specific_charges","")}')
            print(f'  abuse_type:     {c.get("abuse_of_power_type","")}')
            print(f'  ai_summary:     {c.get("ai_summary","")[:120]}')
        return

    output_path = None if args.dry_run else args.output
    enriched = run_enrichment(
        cases=cases,
        model=args.model,
        output_path=output_path,
        concurrency=args.concurrency,
        force=args.force,
        upload=args.upload,
        log=log,
    )
    print_stats(enriched)


if __name__ == '__main__':
    main()
