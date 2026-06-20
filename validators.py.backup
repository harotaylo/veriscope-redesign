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
    'sworn in', 'appointed to', 'confirmed as', 'nominated for',
    'businessman', 'felon with',
    'hometown hero', 'honor', 'award', 'recogni'
]

OFFICIAL_KEYWORDS = [
    'senator', 'representative', 'congressman', 'congresswoman', 'governor', 'mayor',
    'judge', 'magistrate', 'commissioner', 'council member', 'councilman', 'councilwoman',
    'councilmember', 'alderman', 'aldermanic', 'constable',
    'sheriff', 'police chief', 'district attorney', 'attorney general',
    'state representative', 'state senator', 'state treasurer', 'state auditor',
    'superintendent', 'warden', 'jailer', 'county clerk', 'county treasurer',
    'state police', 'state trooper', 'correctional officer', 'correction officer',
    'prison guard', 'police officer', 'police detective', 'detective',
    'deputy sheriff', 'deputy jailer', 'fire chief', 'fire captain',
    'former sheriff', 'former judge', 'former mayor', 'former officer',
    'former deputy', 'former detective', 'former trooper', 'former warden',
    'former chief', 'former councilman', 'former councilmember', 'former commissioner',
    'former prosecutor', 'former agent', 'former police', 'former prison'
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
        
        # Location check - accept any non-empty location including Unknown
        # since press releases are from US federal offices covering US/territories
        location = case.get('location', '').strip()
        if not location:
            case['location'] = 'United States'
        
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
        if not location:
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
