import json
import argparse
import os
from dotenv import load_dotenv
from validators import CaseValidator

load_dotenv()

def load_cases(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, encoding='utf-8') as f:
        return json.load(f)

def save_cases(cases, output_path):
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='VeriScope Ingestion Pipeline')
    parser.add_argument('--input', required=True, help='Input JSON file')
    parser.add_argument('--output', help='Output JSON file')
    
    args = parser.parse_args()
    
    print("Loading cases...")
    cases = load_cases(args.input)
    print(f"Loaded {len(cases)} cases")
    
    print("\nValidating cases...")
    validator = CaseValidator()
    valid_cases = validator.validate(cases)
    validator.report()
    
    if args.output:
        print(f"\nSaving validated cases to {args.output}...")
        save_cases(valid_cases, args.output)
        print(f"✓ Saved {len(valid_cases)} valid cases!")

if __name__ == '__main__':
    main()
