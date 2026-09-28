import json
from collections import defaultdict

with open('scratch/forensic_matches.json') as f:
    matches = json.load(f)

by_file = defaultdict(list)
for m in matches:
    by_file[m['file']].append(m)

print(f"Total files with parameter mentions: {len(by_file)}")
for filename, items in sorted(by_file.items()):
    print(f"\n=== {filename} ({len(items)} matches) ===")
    for item in items[:5]:
        print(f"  Line {item['line']}: {item['text']}")
