#!/usr/bin/env python3
"""
Master state court scraper - runs all 50 states + US territories.
Orchestrates framework + all state implementations.
"""
import json
import time
from datetime import datetime
from state_court_scraper_framework import (
    StateCourtScraper, STATE_SCRAPERS, STATE_NAMES,
    upload_to_supabase
)
from state_court_scrapers_all import ALL_STATE_SCRAPERS, ALL_STATE_NAMES

# Merge all scrapers
ALL_SCRAPERS = {**STATE_SCRAPERS, **ALL_STATE_SCRAPERS}
ALL_STATES = {**STATE_NAMES, **ALL_STATE_NAMES}

def scrape_all_states():
    """Run scrapers for all 50 states + territories."""
    print("\n" + "="*70)
    print("VeriScope - Master State Courts Scraper (All 50 States + Territories)")
    print("="*70)

    all_cases = []
    state_counts = {}
    errors = []

    states_list = sorted(ALL_STATES.items())
    total_states = len(states_list)

    for idx, (state_code, state_name) in enumerate(states_list, 1):
        try:
            print(f"\n[{idx}/{total_states}] {state_name} ({state_code})")

            if state_code in ALL_SCRAPERS:
                scraper_class = ALL_SCRAPERS[state_code]
                scraper = scraper_class(state_code, state_name)
            else:
                print(f"  No scraper for {state_code}, using base class")
                scraper = StateCourtScraper(state_code, state_name)

            cases = scraper.scrape()
            all_cases.extend(cases)
            state_counts[state_code] = len(cases)

            print(f"  ✓ Found: {len(cases)} cases")

            # Rate limit: 1 second between states to avoid overwhelming servers
            if idx < total_states:
                time.sleep(1)

        except Exception as e:
            error_msg = str(e)[:60]
            errors.append(f"{state_code}: {error_msg}")
            print(f"  ✗ Error: {error_msg}")

    # Summary
    print("\n" + "="*70)
    print("SCRAPE SUMMARY")
    print("="*70)
    print(f"\nTotal cases found: {len(all_cases)}")
    print(f"States scraped: {sum(1 for c in state_counts.values() if c > 0)}/{total_states}")

    if state_counts:
        print("\nTop 10 states by case count:")
        for state_code, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {state_code}: {count}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for error in errors[:5]:
            print(f"  {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")

    return all_cases, state_counts

def main():
    all_cases, state_counts = scrape_all_states()

    # Save raw data
    print("\n" + "="*70)
    print("SAVING & UPLOADING")
    print("="*70)

    with open(f'master_state_cases_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_cases': len(all_cases),
            'state_counts': state_counts,
            'cases': all_cases
        }, f, indent=2)
    print(f"Saved raw data")

    # Upload to Supabase
    uploaded = upload_to_supabase(all_cases)

    print(f"\n" + "="*70)
    print(f"SUCCESS: {uploaded} new cases uploaded from {len(state_counts)} states")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
