"""
Supabase Uploader - Gate 2 validation
Validates jurisdiction_id before INSERT
"""

from supabase import create_client
import os

class SupabaseUploader:
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.client = create_client(self.url, self.key)
        self.jurisdiction_map = None
    
    def _get_jurisdiction_map(self):
        if self.jurisdiction_map is None:
            response = self.client.table('jurisdictions').select('*').execute()
            self.jurisdiction_map = {
                row['jurisdiction_code']: row['id']
                for row in response.data
            }
        return self.jurisdiction_map
    
    def _get_jurisdiction_id(self, location):
        if not location:
            return None
        
        jmap = self._get_jurisdiction_map()
        location_upper = location.upper()
        
        if location_upper in jmap:
            return jmap[location_upper]
        
        parts = location.split(',')
        if parts:
            state_code = parts[0].strip().upper()
            if state_code in jmap:
                return jmap[state_code]
        
        for code, jid in jmap.items():
            if code in location_upper:
                return jid
        
        return None
    
    def upload(self, cases, dry_run=False):
        results = {
            'uploaded': 0,
            'duplicates': 0,
            'failed': 0,
            'rejected': 0,
            'details': {'rejected': [], 'failed': []}
        }
        
        for case in cases:
            jurisdiction_id = self._get_jurisdiction_id(case.get('location'))
            
            if not jurisdiction_id:
                results['rejected'] += 1
                results['details']['rejected'].append({
                    'case': case.get('title', 'Unknown'),
                    'reason': f"No valid jurisdiction found"
                })
                continue
            
            case['jurisdiction_id'] = jurisdiction_id
            
            if not dry_run:
                try:
                    self.client.table('cases').insert(case).execute()
                    results['uploaded'] += 1
                except Exception as e:
                    results['failed'] += 1
                    results['details']['failed'].append({
                        'case': case.get('title', 'Unknown'),
                        'error': str(e)
                    })
            else:
                results['uploaded'] += 1
        
        return results
