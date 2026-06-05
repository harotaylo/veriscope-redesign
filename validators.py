"""
Strict validation for public official misconduct cases.
Only cases with actual findings + named officials pass.
"""

REQUIRED_MISCONDUCT = [
    'convicted', 'guilty', 'indicted', 'charged', 'removed', 'suspended', 'censured',
    'plea', 'sentenced', 'acquitted', 'dismissed', 'settlement', 'investigation found',
    'findings against', 'fired', 'resigned'
]

REJECT_KEYWORDS = [
    'sworn in', 'appointed', 'confirmed', 'announced', 'nominated',
    'man pleads', 'woman pleads', 'couple sentenced', 'person guilty',
    'businessman', 'alien', 'national', 'felon with'
]

OFFICIAL_KEYWORDS = [
    'senator', 'representative', 'congressman', 'congresswoman', 'governor', 'mayor',
    'judge', 'commissioner', 'council member', 'councilman', 'councilwoman',
    'sheriff', 'police chief', 'district attorney', 'attorney general',
    'state representative', 'state senator', 'state treasurer', 'state auditor',
    'superintendent', 'director', 'chief', 'captain', 'lieutenant', 'sergeant',
    'warden', 'county clerk', 'county treasurer', 'state police'
]

class CaseValidator:
    def __init__(self):
        self.rejected_cases = []
        self.valid_cases = []
    
    def validate(self, cases):
        """Filter cases for public official misconduct only"""
        for case in cases:
            if self._is_valid(case):
                self.valid_cases.append(case)
            else:
                self.rejected_cases.append({
                    'case': case,
                    'reason': self._get_rejection_reason(case)
                })
        return self.valid_cases
    
    def _is_valid(self, case):
        title = case.get('title', '').lower()
        details = case.get('details', '').lower()
        combined = title + ' ' + details
        
        # Check for disqualifying keywords
        if any(reject in combined for reject in REJECT_KEYWORDS):
            return False
        
        # Must have official keyword
        has_official = any(official in combined for official in OFFICIAL_KEYWORDS)
        if not has_official:
            return False
        
        # Must have misconduct finding
        has_misconduct = any(misconduct in combined for misconduct in REQUIRED_MISCONDUCT)
        if not has_misconduct:
            return False
        
        # Must have location
        location = case.get('location', '').strip()
        if not location or location.lower() == 'unknown':
            return False
        
        return True
    
    def _get_rejection_reason(self, case):
        title = case.get('title', '').lower()
        details = case.get('details', '').lower()
        combined = title + ' ' + details
        
        if any(reject in combined for reject in REJECT_KEYWORDS):
            return 'Contains disqualifying keywords (appointment, nomination, etc.)'
        
        has_official = any(official in combined for official in OFFICIAL_KEYWORDS)
        if not has_official:
            return 'Not a public official'
        
        has_misconduct = any(misconduct in combined for misconduct in REQUIRED_MISCONDUCT)
        if not has_misconduct:
            return 'No misconduct finding'
        
        location = case.get('location', '').strip()
        if not location or location.lower() == 'unknown':
            return 'Unknown location'
        
        return 'Unknown reason'
    
    def report(self):
        """Print validation report"""
        print(f"\n{'='*60}")
        print(f"VALIDATION REPORT")
        print(f"{'='*60}")
        print(f"✓ Valid cases: {len(self.valid_cases)}")
        print(f"✗ Rejected cases: {len(self.rejected_cases)}")
        print(f"\nRejection breakdown:")
        
        reasons = {}
        for rejected in self.rejected_cases:
            reason = rejected['reason']
            reasons[reason] = reasons.get(reason, 0) + 1
        
        for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {reason}: {count}")
        print(f"{'='*60}\n")
