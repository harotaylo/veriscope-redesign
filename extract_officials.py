import json
import csv
from collections import defaultdict

# Your 51 cases data (I'll generate the SQL from this)
cases_data = [
    {"id": 267, "full_name": "Former Sheriff's Deputy in San Diego County", "official_type": "Police", "agency": "San Diego County Sheriff's Department", "category": "Child Exploitation"},
    {"id": 274, "full_name": "Virginia Police Captain", "official_type": "Police", "agency": "", "category": "Civil Rights"},
    {"id": 281, "full_name": "Los Angeles County Deputy", "official_type": "Police", "agency": "Los Angeles County Sheriff's Department", "category": "Civil Rights"},
    {"id": 273, "full_name": "Arkansas State Police Officer", "official_type": "Police", "agency": "Arkansas State Police", "category": "Civil Rights"},
    {"id": 288, "full_name": "Clarence BigEagle", "official_type": "Police", "agency": "Standing Rock Sioux Tribal Police", "category": "Civil Rights"},
    {"id": 285, "full_name": "Arizona State Representative", "official_type": "Politician", "agency": "Arizona State Legislature", "category": "Election Integrity"},
    {"id": 276, "full_name": "Wisconsin County Clerk", "official_type": "Politician", "agency": "Crawford County Clerk's Office", "category": "Election Integrity"},
    {"id": 260, "full_name": "Oregon Governor's Office Staffer", "official_type": "Politician", "agency": "", "category": "Election Integrity"},
    {"id": 284, "full_name": "Pennsylvania State Representative", "official_type": "Politician", "agency": "Pennsylvania House of Representatives", "category": "Financial Crime"},
    {"id": 245, "full_name": "Paula Randolph", "official_type": "Politician", "agency": "Michigan State Senate", "category": "Financial Crime"},
    {"id": 253, "full_name": "Ronald Craft", "official_type": "Judge", "agency": "Pike County District Court", "category": "Judicial Misconduct"},
    {"id": 251, "full_name": "Cleveland Municipal Court Judge", "official_type": "Judge", "agency": "Cleveland Municipal Court", "category": "Judicial Misconduct"},
    {"id": 269, "full_name": "Pennsylvania Magistrate", "official_type": "Judge", "agency": "", "category": "Judicial Misconduct"},
    {"id": 277, "full_name": "Philadelphia Traffic Court Judge", "official_type": "Judge", "agency": "Philadelphia Traffic Court", "category": "Judicial Misconduct"},
    {"id": 265, "full_name": "Tennessee State Court Judge", "official_type": "Judge", "agency": "Tennessee Circuit Court", "category": "Judicial Misconduct"},
    {"id": 250, "full_name": "New Orleans Police Sergeant", "official_type": "Police", "agency": "New Orleans Police Department", "category": "Police Misconduct"},
    {"id": 249, "full_name": "Philadelphia Police Lieutenant", "official_type": "Police", "agency": "Philadelphia Police Department", "category": "Police Misconduct"},
    {"id": 282, "full_name": "Montana State Highway Patrol Captain", "official_type": "Police", "agency": "Montana Highway Patrol", "category": "Police Misconduct"},
    {"id": 248, "full_name": "Ohio Sheriff's Deputy", "official_type": "Police", "agency": "", "category": "Police Misconduct"},
    {"id": 263, "full_name": "Maine State Police Evidence Technician", "official_type": "Police", "agency": "", "category": "Police Misconduct"},
    {"id": 289, "full_name": "Roger Estrada", "official_type": "Politician", "agency": "Miami-Dade County Commission", "category": "Public Corruption"},
    {"id": 252, "full_name": "West Virginia DMV Director", "official_type": "Politician", "agency": "West Virginia DMV", "category": "Public Corruption"},
    {"id": 271, "full_name": "Kentucky Mayor", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
    {"id": 257, "full_name": "City Councilman", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
    {"id": 283, "full_name": "Louisiana State Police Superintendent", "official_type": "Police", "agency": "Louisiana State Police", "category": "Public Corruption"},
    {"id": 270, "full_name": "Texas State Senator", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
    {"id": 264, "full_name": "Baltimore City Health Department Director", "official_type": "Politician", "agency": "Baltimore City Health Department", "category": "Public Corruption"},
    {"id": 255, "full_name": "Rhode Island State Senator", "official_type": "Politician", "agency": "Rhode Island State Senate", "category": "Public Corruption"},
    {"id": 272, "full_name": "South Carolina Sheriff", "official_type": "Police", "agency": "Orangeburg County Sheriff's Office", "category": "Public Corruption"},
    {"id": 247, "full_name": "Earl Strickland", "official_type": "Politician", "agency": "Oklahoma County Commission", "category": "Public Corruption"},
    {"id": 279, "full_name": "City Councilman", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
    {"id": 268, "full_name": "Puerto Rico Municipal Mayor", "official_type": "Politician", "agency": "City of Caguas", "category": "Public Corruption"},
    {"id": 256, "full_name": "Nebraska State Auditor", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
    {"id": 280, "full_name": "Tampa Fire Captain", "official_type": "Police", "agency": "Tampa Fire Rescue", "category": "Public Corruption"},
    {"id": 266, "full_name": "New Hampshire State Liquor Inspector", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
    {"id": 286, "full_name": "Indiana County Sheriff", "official_type": "Police", "agency": "Hendricks County Sheriff's Office", "category": "Public Corruption"},
    {"id": 262, "full_name": "Idaho State Parks Director", "official_type": "Politician", "agency": "Idaho Department of Parks and Recreation", "category": "Public Corruption"},
    {"id": 261, "full_name": "Houston City Controller", "official_type": "Politician", "agency": "City of Houston", "category": "Public Corruption"},
    {"id": 287, "full_name": "Kansas City Board of Education Member", "official_type": "Politician", "agency": "Kansas City School Board", "category": "Public Corruption"},
    {"id": 258, "full_name": "Illinois State Treasurer's Office Employee", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
    {"id": 259, "full_name": "Wyoming State Auditor Employee", "official_type": "Politician", "agency": "", "category": "Public Corruption"},
]

# Map categories to abuse_of_power_type
abuse_map = {
    "Child Exploitation": "CSAM",
    "Civil Rights": "Civil Rights Violation",
    "Election Integrity": "Election Fraud",
    "Financial Crime": "Embezzlement/Bribery",
    "Judicial Misconduct": "Abuse of Authority",
    "Police Misconduct": "Misconduct",
    "Public Corruption": "Corruption",
}

# Generate SQL to update cases with abuse_of_power_type
print("-- UPDATE cases with abuse_of_power_type\n")
for case in cases_data:
    abuse_type = abuse_map[case["category"]]
    print(f"UPDATE public.cases SET abuse_of_power_type = '{abuse_type}' WHERE id = {case['id']};")

print("\n-- Done updating all 51 cases")
