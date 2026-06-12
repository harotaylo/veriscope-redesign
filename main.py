"""
VeriScope Ingestion Pipeline
Full pipeline: Validate -> Transform -> Upload
"""

import json
import sys
from validators import CaseValidator
from transformer import CaseTransformer
from uploader import SupabaseUploader

class VeriScopeIngestionPipeline:
    def __init__(self):
        self.validator = CaseValidator()
        self.transformer = CaseTransformer()
        self.uploader = SupabaseUploader()
        self.metrics = {
            'input': 0, 'validated': 0, 'rejected': 0,
            'transformed': 0, 'uploaded': 0, 'failed': 0
        }
    
    def ingest(self, cases, output_file=None, upload=False, dry_run=False):
        print("\n" + "="*70)
        print("VeriScope Ingestion Pipeline")
        print("="*70)
        print(f"Input cases: {len(cases)}")
        self.metrics['input'] = len(cases)
        
        # STAGE 1: VALIDATION
        print("\n[STAGE 1] VALIDATION - Checking jurisdiction...")
        validation_result = self.validator.validate(cases)
        self.metrics['validated'] = validation_result['valid']
        self.metrics['rejected'] = validation_result['invalid']
        
        print(f"  Valid: {validation_result['valid']}")
        print(f"  Rejected: {validation_result['invalid']}")
        
        valid_cases = validation_result['valid_cases']
        if not valid_cases:
            print("\nNo valid cases. Stopping.")
            return {'success': False}
        
        # STAGE 2: TRANSFORMATION
        print("\n[STAGE 2] TRANSFORMATION - Converting to schema...")
        transformed_cases = self.transformer.transform(valid_cases)
        self.metrics['transformed'] = len(transformed_cases)
        print(f"  Transformed: {len(transformed_cases)}")
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(transformed_cases, f, indent=2)
            print(f"  Saved to: {output_file}")
        
        if not upload:
            return {'success': True, 'stages': 2}
        
        # STAGE 3: UPLOAD
        print("\n[STAGE 3] UPLOAD - Validating jurisdiction & inserting...")
        upload_result = self.uploader.upload(transformed_cases, dry_run=dry_run)
        self.metrics['uploaded'] = upload_result.get('uploaded', 0)
        self.metrics['failed'] = upload_result.get('failed', 0)
        
        print(f"  Uploaded: {upload_result.get('uploaded', 0)}")
        print(f"  Failed: {upload_result.get('failed', 0)}")
        print(f"  Rejected: {upload_result.get('rejected', 0)}")
        
        print("\n" + "="*70)
        print("Status: SUCCESS")
        print("="*70 + "\n")
        
        return {'success': True, 'stages': 3, 'metrics': self.metrics}

if __name__ == "__main__":
    print("Usage: python main.py <cases.json>")
