import json

with open('scratch/forensic_matches.json') as f:
    matches = json.load(f)

print("=== CLASSIFIED OCCURRENCES OF WHEEL / RADIUS / PPR PARAMETERS ===")
seen = set()
for m in matches:
    txt = m['text']
    fpath = m['file']
    if any(k in txt.lower() for k in ['wheel', 'diameter', 'radius', 'ppr', 'pulses_per']):
        key = f"{fpath}:{m['line']}"
        if key not in seen:
            seen.add(key)
            # Classification logic:
            if "backup" in fpath or "V0_1_BASELINE" in fpath or "phase7" in fpath or "STAGE" in fpath:
                cls = "VALID HISTORICAL RECORD"
            elif "test_" in fpath or "tests/" in fpath:
                cls = "TEST FIXTURE"
            elif "canonical" in fpath or "physical_vehicle_parameters" in fpath or "sketch_" in fpath or "VEHICLE_B" in fpath:
                cls = "RECONCILED CANONICAL VALUE"
            else:
                cls = "DOCUMENTED LEGACY VALUE"
            print(f"[{cls:28s}] {fpath}:{m['line']} -> {txt[:80]}")
