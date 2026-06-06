"""
VeriScope Case Ingestion Pipeline
Validates, transforms, and uploads cases to Supabase
"""

import json
import argparse
import os
from dotenv import load_dotenv
from datetime import datetime
from extract_case_status import CaseStatusExtractor
from validators import CaseValidator
from transformer import CaseTransformer

load_dotenv()

class VeriScopeIngestionSystem:
    def __init__(self):
        self.cases = []
        self.ingestion_log = []
        self.status_extractor = CaseStatusExtractor()
        
    def load_cases(self, file_path):
        """Load cases from JSON file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, encoding='utf-8') as f:
            return json.load(f)
    
    def add_case(self, title, full_name, position, official_type, agency, abuse_type, 
                 charges, summary, details, source_url, source_type, date_charged, 
                 location, state_code):
        """Add case with auto-extracted status and corrected date"""
        
        # Auto-extract case status from title and details
        case_status = self.status_extractor.extract_status(title, details)
        
        # Auto-correct bad dates
        corrected_date = self.status_extractor.extract_date(date_charged, details)
        
        case = {
            'title': title,
            'full_name': full_name,
            'position': position,
            'official_type': official_type,
            'agency_or_office': agency,
            'abuse_of_power_type': abuse_type,
            'specific_charges': charges,
            'ai_summary': summary,
            'details': details,
            'source_url': source_url,
            'source_type': source_type,
            'date_charged': corrected_date,
            'case_status': case_status,
            'location': location,
            'state': state_code,
            'category': abuse_type,
            'publication_status': 'draft',
            'verified_by': None,
        }
        
        if self._validate(case):
            self.cases.append(case)
            self.ingestion_log.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'case_added',
                'case': title,
                'status': case_status,
                'date_corrected': corrected_date != date_charged,
                'result': 'success'
            })
            return case
        else:
            self.ingestion_log.append({
                'timestamp': datetime.now().isoformat(),
                'action': 'case_rejected',
                'case': title,
                'result': 'validation_failed'
            })
            return None
    
    def _validate(self, case):
        """Validate case meets VeriScope standards"""
        required = ['full_name', 'position', 'specific_charges', 'source_url', 'location', 'date_charged']
        return all(case.get(field) for field in required)
    
    def save_json(self, cases, filename='gathered_cases.json'):
        """Export cases as JSON"""
        output = {
            'metadata': {
                'generated': datetime.now().isoformat(),
                'total_cases': len(cases),
                'mission': 'Document officials abusing their power',
            },
            'cases': cases
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"✓ Saved {len(cases)} cases to {filename}")
        return filename
    
    def print_report(self):
        """Print ingestion summary"""
        print(f"\n{'='*80}")
        print(f"VERISCOPE CASE INGESTION REPORT")
        print(f"{'='*80}")
        print(f"Total cases processed: {len(self.cases)}")
        print(f"Log entries: {len(self.ingestion_log)}")
        
        # Count status breakdown
        status_counts = {}
        for case in self.cases:
            status = case.get('case_status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\nCase Status Breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        
        # Count date corrections
        corrections = sum(1 for log in self.ingestion_log if log.get('date_corrected'))
        print(f"\nDates corrected: {corrections}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*80}\n")

def main():
    parser = argparse.ArgumentParser(description='VeriScope Case Ingestion Pipeline')
    parser.add_argument('--input', required=True, help='Input JSON file with cases')
    parser.add_argument('--output', help='Output JSON file for processed cases')
    
    args = parser.parse_args()
    
    system = VeriScopeIngestionSystem()
    
    print("VeriScope Case Ingestion Pipeline")
    print("Loading and processing cases...\n")
    
    try:
        cases_data = system.load_cases(args.input)
        print(f"✓ Loaded {len(cases_data)} cases from {args.input}")
        
        # Process each case
        for case in cases_data:
            system.add_case(
                title=case.get('title', ''),
                full_name=case.get('full_name', ''),
                position=case.get('position', ''),
                official_type=case.get('official_type', ''),
                agency=case.get('agency_or_office', ''),
                abuse_type=case.get('abuse_of_power_type', ''),
                charges=case.get('specific_charges', ''),
                summary=case.get('ai_summary', ''),
                details=case.get('details', ''),
                source_url=case.get('source_url', ''),
                source_type=case.get('source_type', 'court_record'),
                date_charged=case.get('date_charged', ''),
                location=case.get('location', ''),
                state_code=case.get('state', '')
            )
        
        system.print_report()
        
        if args.output:
            system.save_json(system.cases, args.output)
        
        print("✓ Ingestion complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    main()
