"""
Extract and infer case status from case details
"""

import re
from datetime import datetime

class CaseStatusExtractor:
    def __init__(self):
        self.status_keywords = {
            'Convicted': ['convicted', 'guilty plea', 'found guilty', 'guilty verdict'],
            'Acquitted': ['acquitted', 'not guilty', 'found not guilty'],
            'Dismissed': ['dismissed', 'charges dismissed', 'case dismissed'],
            'Indicted': ['indicted', 'grand jury', 'federal indictment', 'charged with'],
            'Sentenced': ['sentenced to', 'sentenced for', 'prison time', 'years in prison'],
            'Appealing': ['appealing', 'appeal pending', 'under appeal'],
            'Plea Bargain Reached': ['plea bargain', 'plea agreement', 'pleaded guilty to'],
            'Charged': ['charged with', 'faces charges'],
            'Arrested / Detained': ['arrested', 'detained', 'taken into custody'],
        }
    
    def extract_status(self, title, details):
        """
        Infer case status from title and details
        Returns: status string
        """
        combined = (title + ' ' + details).lower()
        
        # Check in order of specificity (most specific first)
        for status, keywords in self.status_keywords.items():
            if any(kw in combined for kw in keywords):
                return status
        
        # Default to Charged if no other status found
        return 'Charged'
    
    def extract_date(self, date_string, details):
        """
        Extract correct date_charged from date string or details
        Returns: YYYY-MM-DD format
        """
        if not date_string or date_string == '12/31/1969' or date_string == '1969-12-31':
            # Try to find date in details
            date_pattern = r'\b(\d{4})-(\d{2})-(\d{2})\b'
            match = re.search(date_pattern, details)
            if match:
                return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
            
            # Fallback to today if no date found
            return datetime.now().strftime('%Y-%m-%d')
        
        # Clean up the date
        try:
            if 'T' in date_string:
                date_string = date_string.split('T')[0]
            
            # Validate it's not 1969
            if date_string.startswith('1969'):
                return datetime.now().strftime('%Y-%m-%d')
            
            return date_string[:10]
        except:
            return datetime.now().strftime('%Y-%m-%d')

# Example usage
if __name__ == '__main__':
    extractor = CaseStatusExtractor()
    
    # Test with Kentucky Mayor case
    title = "Kentucky Mayor Acquitted in Misconduct Trial"
    details = "Lexington Mayor Diane Foster was acquitted of all charges in a six-week public corruption trial."
    bad_date = "12/31/1969"
    
    status = extractor.extract_status(title, details)
    date = extractor.extract_date(bad_date, details)
    
    print(f"Title: {title}")
    print(f"Extracted Status: {status}")
    print(f"Extracted Date: {date}")
    print()
    
    # Test another case
    title2 = "Michigan State Senator Charged With Insurance Fraud"
    details2 = "Paula Randolph was charged with insurance fraud, false statements, and wire fraud."
    bad_date2 = "12/31/1969"
    
    status2 = extractor.extract_status(title2, details2)
    date2 = extractor.extract_date(bad_date2, details2)
    
    print(f"Title: {title2}")
    print(f"Extracted Status: {status2}")
    print(f"Extracted Date: {date2}")
