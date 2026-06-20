# VeriScope Database Validator

Complete validation system for VeriScope database with two modes:

## Overview

The validator ensures data quality across the pipeline and existing database:

1. **Pipeline Validator** — Checks new data before upload
2. **Database Auditor** — Audits existing records in Supabase
3. **Integrated Validation** — Runs automatically in enhanced pipeline

## Files

- `database_validator.py` — Standalone validator (run manually)
- `veriscope_pipeline_with_validation.py` — Pipeline with integrated validation
- `VALIDATOR_USAGE.md` — This file

## Quick Start

### Option 1: Standalone Validation (Audit Existing Database)

```bash
python database_validator.py
```

This runs:
- Validates all pipeline output JSON files (if they exist)
- Audits all 4,890 records currently in Supabase
- Generates comprehensive validation report

**Output:**
- `validation_report_YYYYMMDD_HHMMSS.json` — Full report with errors/warnings

### Option 2: Enhanced Pipeline (With Built-in Validation)

```bash
python veriscope_pipeline_with_validation.py
```

This runs the normal pipeline but **STOPS before upload** if validation fails:
- Scrapes cases
- Validates & deduplicates
- **NEW:** Validates all data before upload (80% pass rate required)
- Uploads only if validation passes
- Saves validation report with pre-upload results

**Output:**
- `01_raw.json` — All scraped cases
- `02_validated.json` — Cases passing basic filters
- `03_deduplicated.json` — Unique cases
- `04_ready_for_upload.json` — Cases ready for Supabase
- `pre_upload_validation_*.json` — Validation report
- `upload_log_*.json` — Upload results

## What Gets Validated

### Required Fields
```
full_name, position_title, official_type, jurisdiction_id,
source_type, source_date, publication_status, case_status
```

### Type Checks
- `jurisdiction_id` must be integer (1-58)
- All text fields must be strings
- Dates must be YYYY-MM-DD format

### Enum Constraints
- **source_type**: news_article, court_record, official_report, ngo_report, public_database, other
- **publication_status**: draft, verified, published, retracted
- **official_type**: Executive, Legislative, Judicial, Law Enforcement
- **case_status**: 19 valid statuses (Charged, Convicted, Indicted, etc.)

### Data Quality Checks
- Text length limits (e.g., full_name max 255 chars)
- Missing/empty critical fields
- Invalid date formats
- Invalid jurisdiction references
- Duplicate fingerprints
- URL format validation

### Referential Integrity
- Jurisdiction IDs exist in jurisdictions table
- Foreign key constraints checked

## Report Format

Each validation report includes:

```json
{
  "timestamp": "2026-06-20T14:30:00",
  "stats": {
    "total_records": 4890,
    "valid_records": 4850,
    "error_records": 10,
    "warning_records": 30
  },
  "summary": {
    "total_errors": 10,
    "total_warnings": 30,
    "pass_rate": "99.2%"
  },
  "errors": [
    {
      "type": "error",
      "record_id": "123",
      "field": "case_status",
      "message": "Invalid enum value: 'BadStatus'"
    }
  ],
  "warnings": [
    {
      "type": "warning",
      "record_id": "456",
      "field": "location",
      "message": "Missing location (non-critical)"
    }
  ],
  "info": [
    "Publication status: 4200 draft, 650 verified, 40 published",
    "Top case statuses: Charged: 2100, Convicted: 1200, Indicted: 800"
  ]
}
```

## Integration with Windows Task Scheduler

The enhanced pipeline can be scheduled to run daily at 3 AM:

```batch
cd C:\Users\Ms.Agnew\veriscope-ingestion
python veriscope_pipeline_with_validation.py
```

This ensures:
- New data is validated before upload
- Only quality data reaches Supabase
- Validation reports are generated for review

## Common Issues & Solutions

### Issue: Pass rate below 80% - upload stopped
**Solution:** Review `pre_upload_validation_*.json` errors, fix data quality issues in scraper, retry.

### Issue: Fingerprint duplicates detected
**Solution:** Check if case already exists in database. Deduplicate logic should catch this; if not, check fingerprint calculation.

### Issue: Invalid jurisdiction_id
**Solution:** Check location string mapping. Ensure state names match jurisdiction_map in pipeline.

### Issue: Missing required fields
**Solution:** Check that scraper extracts all required fields. Some sources may not provide all data; set reasonable defaults.

## Custom Validation

To add custom validation rules, edit `database_validator.py`:

1. Add check in `PipelineValidator.validate_record()` method
2. Or add check in `DatabaseAuditor._audit_record()` method
3. Use `self.report.add_error()` or `self.report.add_warning()`

Example:
```python
# Add custom check
if record.get('case_status') == 'Convicted' and not record.get('date_resolved'):
    self.report.add_warning(record_id, 'date_resolved', 
        "Convicted case should have resolution date")
```

## Performance

- **Pipeline validation**: ~100ms for 100 records
- **Database audit**: ~30-60 seconds for 4,890 records
- Reports capped at 100 errors, 50 warnings (for readability)

## Next Steps

1. Run `python database_validator.py` to audit current database
2. Review findings in `validation_report_*.json`
3. Fix any data quality issues
4. Switch pipeline to use `veriscope_pipeline_with_validation.py`
5. Schedule enhanced pipeline in Task Scheduler for daily 3 AM runs
6. Monitor validation reports for ongoing quality
