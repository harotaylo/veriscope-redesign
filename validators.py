"""
Validators for VeriScope Ingestion Pipeline
Rejects foreign jurisdictions and non-US cases
"""

class CaseValidator:
    FOREIGN_INDICATORS = [
        'cambodia', 'cambodian', 'phnom penh',
        'iran', 'iranian', 'tehran',
        'hong kong', 'china', 'chinese',
        'vietnam', 'vietnamese', 'thailand', 'thai',
        'omaliss keo', 'masphal kry',
        'alireza shavaroghi', 'mahmoud khazein', 'kiya sadeghi', 'niloufar bahadorifar'
    ]
    
    US_JURISDICTIONS = {
        'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California',
        'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia',
        'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
        'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland',
        'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri',
        'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey',
        'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
        'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina',
        'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
        'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming',
        'District of Columbia', 'Washington DC',
        'Puerto Rico', 'Virgin Islands', 'Guam', 'Northern Mariana Islands', 'American Samoa'
    }
    
    def __init__(self):
        self.valid_cases = []
        self.invalid_cases = []
    
    def is_us_jurisdiction(self, case):
        location = case.get('location', '').lower()
        details = case.get('details', '').lower()
        
        for indicator in self.FOREIGN_INDICATORS:
            if indicator in details:
                return False, f"Foreign jurisdiction detected in details"
        
        if location:
            location_upper = location.upper()
            for jurisdiction in self.US_JURISDICTIONS:
                if jurisdiction.upper() in location_upper:
                    return True, "Valid US jurisdiction"
        
        return False, f"No valid US jurisdiction found"
    
    def validate(self, cases):
        self.valid_cases = []
        self.invalid_cases = []
        
        for case in cases:
            is_valid, reason = self.is_us_jurisdiction(case)
            if is_valid:
                self.valid_cases.append(case)
            else:
                self.invalid_cases.append({
                    'title': case.get('title', 'Unknown'),
                    'location': case.get('location', 'Unknown'),
                    'reason': reason
                })
        
        return {
            'valid': len(self.valid_cases),
            'invalid': len(self.invalid_cases),
            'valid_cases': self.valid_cases,
            'invalid_cases': self.invalid_cases
        }
