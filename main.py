"""
VeriScope Ingestion Pipeline - Main orchestrator
"""

import json
import argparse
import os
from dotenv import load_dotenv
from validators import CaseValidator
from transformer import CaseTransformer
from uploader import SupabaseUploader

load_dotenv()

def load_cases(file_path):
    """Load cases from JSON file"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path) as f:
        return json.load(f)

def save_cases(cases, output_path):
    """Save cases to JSON file"""
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(cases, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='VeriScope Ingestion Pipeline')
    parser.add_argument('--input', required=True, help='Input JSON file with cases')
    parser.add_argument('--output', help='Output JSON file for validated cases')
    parser.add_argument('--supabase', action='store_true', help='Upload to Supabase')
    parser.add_argument('--dry-run', action='store_true', help='Test without uploading')
    
    args = parser.parse_args()
    
    print("Loading cases...")
    cases = load_cases(args.input)
    print(f"Loaded {len(cases)} cases")
    
    print("\nValidating cases...")
    validator = CaseValidator()
    valid_cases = validator.validate(cases)
    validator.report()
    
    print("Transforming cases...")
    transformer = CaseTransformer()
    transformed_cases = transformer.transform(valid_cases)
    print(f"Transformed {len(transformed_cases)} cases")
    
    if args.output:
        print(f"\nSaving to {args.output}...")
        save_cases(transformed_cases, args.output)
        print("Saved")
    
    if args.supabase:
        print("\nUploading to Supabase...")
        uploader = SupabaseUploader()
        result = uploader.upload(transformed_cases, dry_run=args.dry_run)
        uploader.report(result)

if __name__ == '__main__':
    main()
