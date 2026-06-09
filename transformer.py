"""
Transform raw case data into Supabase schema format.
"""

from datetime import datetime
import hashlib

class CaseTransformer:
    def transform(self, cases):
        """Convert validated cases to Supabase insert format"""
        transformed = []
        for case in cases:
            transformed.append(self._transform_case(case))
        return transformed
    
    def _transform_case(self, case):
        """Transform single case — prefers enriched top-level fields from claude_enricher."""
        # Use enriched top-level fields (set by claude_enricher or scrapers directly).
        # Fall back to entities[] only if top-level fields are absent (legacy path).
        full_name = case.get('full_name', '') or ''
        first_name = case.get('first_name', '') or ''
        last_name = case.get('last_name', '') or ''

        if not full_name and case.get('entities'):
            for entity in case['entities']:
                if entity.get('type') == 'person' and entity.get('name'):
                    full_name = entity['name']
                    break

        if not first_name and full_name and full_name.lower() not in ('unknown', 'unknown official'):
            parts = full_name.split()
            first_name = parts[0] if parts else ''
            last_name = parts[-1] if len(parts) > 1 else ''

        agency_or_office = case.get('agency_or_office', '') or ''
        if not agency_or_office and case.get('entities'):
            for entity in case['entities']:
                if entity.get('office'):
                    agency_or_office = entity['office']
                    break

        # Prefer enriched level/location; fall back to heuristic determination.
        level = case.get('level') or self._determine_level(case)
        location = case.get('location', 'Unknown') or 'Unknown'

        date_str = self._parse_date(
            case.get('date_charged') or case.get('occurred_at') or case.get('source_date')
        )
        source_date_str = self._parse_date(
            case.get('source_date') or case.get('ingested_at') or date_str
        )

        # Preserve the original scraper fingerprint — do not regenerate.
        fingerprint = case.get('fingerprint') or self._generate_fingerprint(
            full_name, case.get('title', ''), date_str
        )

        return {
            'title':              case.get('title', ''),
            'full_name':          full_name,
            'first_name':         first_name,
            'last_name':          last_name,
            'agency_or_office':   agency_or_office,
            'level':              level,
            'location':           location,
            'specific_charges':   case.get('specific_charges', ''),
            'summary':            case.get('ai_summary', ''),
            'ai_summary':         case.get('ai_summary', ''),
            'details':            case.get('details', ''),
            'risk_score':         case.get('risk_score', 0.5),
            'date':               date_str,
            'category':           case.get('category', ''),
            'source_url':         case.get('source_url', ''),
            'source_type':        case.get('source_type', 'official_report'),
            'source_date':        source_date_str,
            'source_notes':       case.get('source_notes', ''),
            'fingerprint':        fingerprint,
            'publication_status': 'draft',
            'verified_by':        case.get('verified_by'),
            'verified_at':        case.get('verified_at'),
        }
    
    def _determine_level(self, case):
        """Determine jurisdiction level from case data"""
        title = case.get('title', '').lower()
        agency = case.get('entities', [{}])[0].get('office', '').lower() if case.get('entities') else ''
        source_url = case.get('source_url', '').lower()
        
        if 'federal' in title or 'u.s.' in title or 'justice.gov' in source_url:
            return 'Federal'
        elif 'state' in title or 'state' in agency:
            return 'State'
        elif 'county' in title or 'county' in agency:
            return 'County'
        elif 'city' in title or 'municipal' in title:
            return 'Local'
        else:
            return 'State'
    
    def _parse_date(self, date_str):
        """Parse date string to YYYY-MM-DD format"""
        if not date_str:
            return '2026-01-01'
        if 'T' in date_str:
            return date_str.split('T')[0]
        return date_str[:10] if len(date_str) >= 10 else '2026-01-01'
    
    def _generate_fingerprint(self, full_name, title, date):
        """Generate fingerprint for deduplication"""
        combined = f"{full_name}_{title}_{date}".lower()
        return hashlib.md5(combined.encode()).hexdigest()
