import json
from validators import CaseValidator
from transformer import CaseTransformer

with open('cases.json', 'r') as f:
    cases = json.load(f)

print("\n" + "="*70)
print("VeriScope Pipeline Test - Validation Only")
print("="*70)
print(f"Total input cases: {len(cases)}")

validator = CaseValidator()
result = validator.validate(cases)

print("\n[STAGE 1] VALIDATION")
print(f"  Valid cases: {result['valid']}")
print(f"  Rejected cases: {result['invalid']}")

if result['invalid'] > 0:
    print("\n  First 5 rejected:")
    for r in result['invalid_cases'][:5]:
        print(f"    - {r['title'][:50]}")
        print(f"      Location: {r['location']}")
        print(f"      Reason: {r['reason']}")

print("\n[STAGE 2] TRANSFORMATION")
transformer = CaseTransformer()
transformed = transformer.transform(result['valid_cases'])
print(f"  Transformed: {len(transformed)}")

with open('validated_cases.json', 'w') as f:
    json.dump(transformed, f, indent=2)
print(f"  Saved to: validated_cases.json")

print("\n" + "="*70)
print("Status: SUCCESS")
print("="*70 + "\n")
