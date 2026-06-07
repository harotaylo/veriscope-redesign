import json
import re

def extract_name_from_details(details, title):
    if not details:
        return None, None, None

    patterns = [
        r"([A-Z][a-z]+\s+[A-Z][a-z]+),\s+(?:\d+),",
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:was|is)\s+(?:arrested|charged|convicted|indicted|sentenced)",
        r"announced\s+(?:today\s+)?(?:that\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+),",
    ]

    for pattern in patterns:
        match = re.search(pattern, details)
        if match:
            name = match.group(1).strip()
            parts = name.split()
            first = parts[0]
            last = " ".join(parts[1:])
            return first, last, name

    return None, None, None

with open("validated_cases.json") as f:
    cases = json.load(f)

print(f"Processing {len(cases)} cases...\n")

updated = 0
for case in cases:
    if not case.get("full_name") or case["full_name"] == "":
        first, last, full = extract_name_from_details(case.get("details", ""), case.get("title", ""))
        if first and last:
            case["first_name"] = first
            case["last_name"] = last
            case["full_name"] = full
            updated += 1
            if updated <= 5:
                print(f"Updated: {full}")

print(f"\nTotal updated: {updated} cases")

with open("cases_with_names.json", "w") as f:
    json.dump(cases, f, indent=2)

print("Saved to cases_with_names.json")
