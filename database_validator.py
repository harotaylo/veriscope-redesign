"""
VeriScope Database Validator
Validates both pipeline data and existing Supabase records
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple
from supabase import create_client
import re

# Supabase config
SUPABASE_URL = "https://sqaibfaniwbixviptilx.supabase.co"
SUPABASE_KEY = "sb_publishable_xopITtNbV8D0CGRi0Qq1kg_5wLInWPJ"

# Schema constraints
REQUIRED_FIELDS = {
    'full_name': str,
    'position_title': str,
    'official_type': str,
    'jurisdiction_id': int,
    'source_type': str,
    'source_date': str,
    'publication_status': str,
    'case_status': str,
}

ENUM_CONSTRAINTS = {
    'source_type': ['news_article', 'court_record', 'official_report', 'ngo_report', 'public_database', 'other'],
    'publication_status': ['draft', 'verified', 'published', 'retracted'],
    'case_status': [
        'Under Investigation', 'Arrested / Detained', 'Booked', 'Charges Filed',
        'Indicted', 'Arraigned', 'Bail/Bond Set', 'Discovery', 'Pre-Trial Motions',
        'Diversion / Deferred Adjudication', 'Awaiting Trial', 'Plea Bargain Reached',
        'Dismissed', 'Acquitted', 'Convicted', 'Sentenced', 'Appealing',
        'Parole / Probation', 'Closed / Disposed'
    ],
    'official_type': ['Executive', 'Legislative', 'Judicial', 'Law Enforcement'],
    'level': ['Federal', 'State', 'Local', 'County']
}

TEXT_LENGTH_LIMITS = {
    'full_name': 255,
    'title': 500,
    'position_title': 255,
    'location': 255,
    'category': 255,
    'details': 2000,
    'source_url': 2048,
}

class ValidationReport:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.stats = {
            'total_records': 0,
            'valid_records': 0,
            'error_records': 0,
            'warning_records': 0,
        }

    def add_error(self, record_id: str, field: str, message: str):
        self.errors.append({
            'type': 'error',
            'record_id': record_id,
            'field': field,
            'message': message
        })
        self.stats['error_records'] += 1

    def add_warning(self, record_id: str, field: str, message: str):
        self.warnings.append({
            'type': 'warning',
            'record_id': record_id,
            'field': field,
            'message': message
        })
        self.stats['warning_records'] += 1

    def add_info(self, message: str):
        self.info.append({'type': 'info', 'message': message})

    def to_dict(self):
        return {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'summary': {
                'total_errors': len(self.errors),
                'total_warnings': len(self.warnings),
                'pass_rate': f"{100 * self.stats['valid_records'] / max(self.stats['total_records'], 1):.1f}%"
            },
            'errors': self.errors[:100],  # Cap at 100 for readability
            'warnings': self.warnings[:50],
            'info': self.info
        }

class PipelineValidator:
    """Validates new data before upload"""

    def __init__(self):
        self.report = ValidationReport()

    def validate_record(self, record: Dict[str, Any], record_id: int) -> bool:
        """Validate a single record against schema"""
        is_valid = True

        # Check required fields
        for field, field_type in REQUIRED_FIELDS.items():
            if field not in record:
                self.report.add_error(str(record_id), field, f"Missing required field")
                is_valid = False
            elif record[field] is None:
                self.report.add_error(str(record_id), field, f"Required field is null")
                is_valid = False

        # Check field types
        for field, field_type in REQUIRED_FIELDS.items():
            if field in record and record[field] is not None:
                if field_type == int:
                    if not isinstance(record[field], int):
                        self.report.add_error(str(record_id), field, f"Expected int, got {type(record[field]).__name__}")
                        is_valid = False
                elif field_type == str:
                    if not isinstance(record[field], str):
                        self.report.add_error(str(record_id), field, f"Expected str, got {type(record[field]).__name__}")
                        is_valid = False

        # Check enum constraints
        for field, allowed_values in ENUM_CONSTRAINTS.items():
            if field in record and record[field] is not None:
                if record[field] not in allowed_values:
                    self.report.add_error(
                        str(record_id), field,
                        f"Invalid value '{record[field]}'. Must be one of: {', '.join(allowed_values)}"
                    )
                    is_valid = False

        # Check text length limits
        for field, max_len in TEXT_LENGTH_LIMITS.items():
            if field in record and isinstance(record[field], str):
                if len(record[field]) > max_len:
                    self.report.add_warning(
                        str(record_id), field,
                        f"Text exceeds {max_len} chars (has {len(record[field])})"
                    )

        # Validate date formats
        date_fields = ['source_date', 'date_charged', 'date_resolved', 'arrest_date']
        for field in date_fields:
            if field in record and record[field] is not None:
                if not self._is_valid_date(record[field]):
                    self.report.add_error(str(record_id), field, f"Invalid date format: {record[field]}")
                    is_valid = False

        # Validate jurisdiction_id
        if 'jurisdiction_id' in record and isinstance(record['jurisdiction_id'], int):
            if record['jurisdiction_id'] < 1 or record['jurisdiction_id'] > 58:
                self.report.add_warning(
                    str(record_id), 'jurisdiction_id',
                    f"Jurisdiction ID {record['jurisdiction_id']} may be invalid (valid range: 1-58)"
                )

        # Validate fingerprint uniqueness
        if 'fingerprint' in record and not record['fingerprint']:
            self.report.add_warning(str(record_id), 'fingerprint', "Empty fingerprint")

        return is_valid

    def validate_batch(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a batch of records"""
        self.report.stats['total_records'] = len(records)

        for idx, record in enumerate(records):
            if self.validate_record(record, idx):
                self.report.stats['valid_records'] += 1

        return self.report.to_dict()

    @staticmethod
    def _is_valid_date(date_str: str) -> bool:
        """Check if string is valid date (YYYY-MM-DD)"""
        try:
            datetime.strptime(str(date_str), '%Y-%m-%d')
            return True
        except:
            return False

class DatabaseAuditor:
    """Audits existing records in Supabase"""

    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.report = ValidationReport()

    def audit_all_records(self, limit: int = None) -> Dict[str, Any]:
        """Audit all records in database"""
        try:
            # Fetch all records with pagination
            query = self.supabase.table('cases').select('*')

            if limit:
                response = query.limit(limit).execute()
            else:
                # Fetch all (with large limit)
                response = query.limit(10000).execute()

            records = response.data
            self.report.stats['total_records'] = len(records)

            print(f"\n[AUDIT] Analyzing {len(records)} records from Supabase...")

            # Check each record
            for idx, record in enumerate(records):
                self._audit_record(record, idx)

                if (idx + 1) % 500 == 0:
                    print(f"  Processed {idx + 1}/{len(records)}...")

            # Audit referential integrity
            self._check_referential_integrity(records)

            # Audit data quality patterns
            self._check_data_patterns(records)

            self.report.add_info(f"Audit complete: {len(records)} records analyzed")

            return self.report.to_dict()

        except Exception as e:
            self.report.add_error('AUDIT', 'database', f"Failed to fetch records: {str(e)}")
            return self.report.to_dict()

    def _audit_record(self, record: Dict[str, Any], idx: int):
        """Audit a single record"""
        record_id = record.get('id', idx)

        # Check required fields
        for field in REQUIRED_FIELDS.keys():
            if field not in record or record[field] is None:
                self.report.add_error(str(record_id), field, "Missing or null required field")
            elif isinstance(record[field], str) and not record[field].strip():
                self.report.add_warning(str(record_id), field, "Empty string value")

        # Check enum values
        for field, allowed in ENUM_CONSTRAINTS.items():
            if field in record and record[field] is not None:
                if record[field] not in allowed:
                    self.report.add_error(
                        str(record_id), field,
                        f"Invalid enum value: '{record[field]}'"
                    )

        # Check fingerprint
        if not record.get('fingerprint'):
            self.report.add_warning(str(record_id), 'fingerprint', "Missing fingerprint (should be set for dedup)")

        # Check foreign key references
        fk_fields = {
            'jurisdiction_id': (1, 58),  # Valid jurisdiction range
            'official_id': None,  # Optional but should be valid if set
        }

        for fk_field, valid_range in fk_fields.items():
            if fk_field in record and record[fk_field] is not None:
                if valid_range and isinstance(record[fk_field], int):
                    min_val, max_val = valid_range
                    if not (min_val <= record[fk_field] <= max_val):
                        self.report.add_warning(
                            str(record_id), fk_field,
                            f"Foreign key {record[fk_field]} outside valid range {min_val}-{max_val}"
                        )

        # Check data quality
        full_name = record.get('full_name', '').strip()
        if full_name and len(full_name) < 3:
            self.report.add_warning(str(record_id), 'full_name', "Name too short (< 3 chars)")

        position = record.get('position_title', '').strip()
        if position and len(position) < 2:
            self.report.add_warning(str(record_id), 'position_title', "Position too short")

        # Check dates
        if 'source_date' in record and record['source_date']:
            if not PipelineValidator._is_valid_date(record['source_date']):
                self.report.add_error(str(record_id), 'source_date', f"Invalid date format")

        # Check source URL
        source_url = record.get('source_url', '')
        if source_url and not (source_url.startswith('http://') or source_url.startswith('https://')):
            self.report.add_warning(str(record_id), 'source_url', "URL doesn't start with http(s)")

        # Successful audit
        if not self.report.errors or not any(e['record_id'] == str(record_id) for e in self.report.errors):
            self.report.stats['valid_records'] += 1

    def _check_referential_integrity(self, records: List[Dict]):
        """Check foreign key constraints"""
        # Build set of valid jurisdiction IDs
        try:
            jur_response = self.supabase.table('jurisdictions').select('id').execute()
            valid_jurisdiction_ids = {row['id'] for row in jur_response.data}

            invalid_jur = []
            for record in records:
                jur_id = record.get('jurisdiction_id')
                if jur_id and jur_id not in valid_jurisdiction_ids:
                    invalid_jur.append(record['id'])

            if invalid_jur:
                self.report.add_warning(
                    'BATCH',
                    'jurisdiction_id',
                    f"Found {len(invalid_jur)} records with invalid jurisdiction_id"
                )
        except Exception as e:
            self.report.add_info(f"Couldn't check jurisdiction integrity: {str(e)}")

    def _check_data_patterns(self, records: List[Dict]):
        """Check for data quality patterns"""
        stats = {
            'missing_names': 0,
            'missing_positions': 0,
            'missing_locations': 0,
            'duplicate_fingerprints': 0,
            'draft_vs_published': {'draft': 0, 'verified': 0, 'published': 0, 'retracted': 0},
            'status_distribution': {}
        }

        fingerprints = {}
        for record in records:
            # Name check
            if not record.get('full_name', '').strip():
                stats['missing_names'] += 1

            # Position check
            if not record.get('position_title', '').strip():
                stats['missing_positions'] += 1

            # Location check
            if not record.get('location', '').strip():
                stats['missing_locations'] += 1

            # Fingerprint duplicate check
            fp = record.get('fingerprint')
            if fp:
                if fp in fingerprints:
                    stats['duplicate_fingerprints'] += 1
                else:
                    fingerprints[fp] = record['id']

            # Publication status
            pub_status = record.get('publication_status', 'unknown')
            if pub_status in stats['draft_vs_published']:
                stats['draft_vs_published'][pub_status] += 1

            # Case status distribution
            case_status = record.get('case_status', 'Unknown')
            stats['status_distribution'][case_status] = stats['status_distribution'].get(case_status, 0) + 1

        # Report pattern findings
        if stats['missing_names'] > 0:
            self.report.add_warning('BATCH', 'full_name', f"{stats['missing_names']} records missing name")

        if stats['missing_positions'] > 0:
            self.report.add_warning('BATCH', 'position_title', f"{stats['missing_positions']} records missing position")

        if stats['missing_locations'] > 0:
            self.report.add_info(f"{stats['missing_locations']} records missing location (non-critical)")

        if stats['duplicate_fingerprints'] > 0:
            self.report.add_warning('BATCH', 'fingerprint', f"{stats['duplicate_fingerprints']} duplicate fingerprints detected")

        # Publication status info
        self.report.add_info(
            f"Publication status: {stats['draft_vs_published']['draft']} draft, "
            f"{stats['draft_vs_published']['verified']} verified, "
            f"{stats['draft_vs_published']['published']} published"
        )

        # Top case statuses
        top_statuses = sorted(stats['status_distribution'].items(), key=lambda x: x[1], reverse=True)[:5]
        status_str = ', '.join([f"{s[0]}: {s[1]}" for s in top_statuses])
        self.report.add_info(f"Top case statuses: {status_str}")

def validate_pipeline_json(file_path: str) -> Dict[str, Any]:
    """Validate a JSON file from pipeline output"""
    print(f"\n[PIPELINE] Validating: {file_path}")

    try:
        with open(file_path, 'r') as f:
            records = json.load(f)

        if not isinstance(records, list):
            records = [records]

        validator = PipelineValidator()
        return validator.validate_batch(records)

    except Exception as e:
        report = ValidationReport()
        report.add_error('FILE', 'load', f"Failed to load file: {str(e)}")
        return report.to_dict()

def main():
    print("\n" + "="*70)
    print("VeriScope Database Validator")
    print("="*70)

    # Validate pipeline outputs if they exist
    pipeline_files = [
        '01_raw.json',
        '02_validated.json',
        '03_deduplicated.json',
        '04_ready_for_upload.json'
    ]

    pipeline_reports = {}
    for file in pipeline_files:
        if os.path.exists(file):
            report = validate_pipeline_json(file)
            pipeline_reports[file] = report
            print(f"\n{file}:")
            print(f"  Total: {report['stats']['total_records']}")
            print(f"  Valid: {report['stats']['valid_records']}")
            print(f"  Errors: {len(report['errors'])}")
            print(f"  Warnings: {len(report['warnings'])}")

    # Audit existing database
    print("\n" + "="*70)
    print("AUDITING EXISTING DATABASE")
    print("="*70)

    auditor = DatabaseAuditor()
    db_report = auditor.audit_all_records()

    print(f"\nDatabase Audit Results:")
    print(f"  Total records: {db_report['stats']['total_records']}")
    print(f"  Valid records: {db_report['stats']['valid_records']}")
    print(f"  Errors found: {len(db_report['errors'])}")
    print(f"  Warnings found: {len(db_report['warnings'])}")
    print(f"  Pass rate: {db_report['summary']['pass_rate']}")

    # Save comprehensive report
    full_report = {
        'timestamp': datetime.now().isoformat(),
        'pipeline_validations': pipeline_reports,
        'database_audit': db_report,
    }

    report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(full_report, f, indent=2)

    print(f"\n✓ Full report saved to: {report_file}")

    # Print detailed errors
    if db_report['errors']:
        print(f"\n[ERRORS] First 10 errors:")
        for error in db_report['errors'][:10]:
            print(f"  Record {error['record_id']}: {error['field']} - {error['message']}")

    if db_report['warnings']:
        print(f"\n[WARNINGS] First 10 warnings:")
        for warning in db_report['warnings'][:10]:
            print(f"  Record {warning['record_id']}: {warning['field']} - {warning['message']}")

    print("\n" + "="*70)
    print("✅ VALIDATION COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
