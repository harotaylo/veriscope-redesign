"""
Upload validated and transformed cases to Supabase.
"""

from supabase import create_client
import os
from datetime import datetime

class SupabaseUploader:
    def __init__(self):
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        
        self.client = create_client(url, key)
    
    def upload(self, cases, dry_run=False):
        """Upload cases to Supabase"""
        uploaded = []
        failed = []
        duplicates = []
        
        for case in cases:
            try:
                # Check for duplicate by fingerprint
                existing = self.client.table('cases').select('id').eq(
                    'fingerprint', case['fingerprint']
                ).execute()
                
                if existing.data:
                    duplicates.append({
                        'case': case['title'],
                        'reason': 'Duplicate fingerprint'
                    })
                    continue
                
                if not dry_run:
                    # Insert case
                    response = self.client.table('cases').insert(case).execute()
                    uploaded.append(case['title'])
                else:
                    uploaded.append(case['title'])
            
            except Exception as e:
                failed.append({
                    'case': case['title'],
                    'error': str(e)
                })
        
        return {
            'uploaded': len(uploaded),
            'failed': len(failed),
            'duplicates': len(duplicates),
            'details': {
                'uploaded': uploaded,
                'failed': failed,
                'duplicates': duplicates
            }
        }
    
    def report(self, result):
        """Print upload report"""
        print(f"\n{'='*60}")
        print(f"UPLOAD REPORT")
        print(f"{'='*60}")
        print(f"✓ Uploaded: {result['uploaded']}")
        print(f"✗ Failed: {result['failed']}")
        print(f"⚠ Duplicates skipped: {result['duplicates']}")
        
        if result['failed'] > 0:
            print(f"\nFailed cases:")
            for item in result['details']['failed']:
                print(f"  - {item['case']}: {item['error']}")
        
        print(f"{'='*60}\n")
