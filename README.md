# VeriScope Ingestion Pipeline

Automated data pipeline for ingesting, validating, and uploading public official misconduct cases to Supabase.

## Features

- **Strict validation**: Only public officials with actual misconduct findings
- **Data transformation**: Converts raw data to Supabase schema
- **Conflict detection**: Fingerprint-based deduplication
- **Audit logging**: Tracks all ingestion operations
- **Extensible**: Easy to add new data sources

## Data Sources

- Court records (PACER, state databases)
- Case JSON/CSV files
- Public records databases
- Future: Automated court scrapers

## Setup

```bash
git clone https://github.com/harotaylo/veriscope-ingestion.git
cd veriscope-ingestion
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase credentials
python main.py --input cases.json
```

## Pipeline Flow

1. **Validator** (`validators.py`) — Filters for public officials only
2. **Transformer** (`transformer.py`) — Converts to Supabase schema
3. **Deduplicator** (`deduplicator.py`) — Prevents duplicate entries
4. **Uploader** (`uploader.py`) — Inserts into Supabase

## Usage

```bash
# Ingest from JSON file
python main.py --input cases.json --output verified_cases.json

# Ingest and upload directly to Supabase
python main.py --input cases.json --supabase
```

## Environment Variables

See `.env.example` for required variables.
