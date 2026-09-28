import json

with open('scratch/forensic_matches.json') as f:
    matches = json.load(f)

print("=== CODE MATCHES ===")
for m in matches:
    fpath = m['file']
    if any(fpath.endswith(ext) for ext in ['.py', '.json', '.ino', '.yaml']):
        txt = m['text']
        if any(term.lower() in txt.lower() for term in ['ppr', '0.085', '0.10', '0.05', '0.0425', '34.58', 'wheel_diameter', 'pulses_per']):
            print(f"{fpath}:{m['line']} -> {txt[:110]}")
