"""
PHASE 7.3.5 — Canonical Number Forensic Search Script
Audits the repository for all occurrences of target numbers, finds contradictions,
and establishes the exact provenance of each value.
"""

import os
import re
import pandas as pd

SEARCH_TERMS = [
    "1591.4", "1589.2", "1171.2", "1169.6", "35.88", "35.9",
    "2.7856", "2.7466", "550000", "550 kN", "550kN",
    "1.2", "1.2000", "5.0", "5 m", "5m",
    "437.1", "475", "250", "350", "1647", "200",
    "625.4", "141.6", "713.6", "630.8", "11.60", "77.36",
    "22.52", "817.8", "587.2", "99.1", "41.2",
    "BH100", "165000", "165500", "91500", "74000",
    "0.34", "0.020", "0.025"
]

EXTENSIONS = [".py", ".md", ".yaml", ".yml", ".csv", ".json"]
EXCLUDE_DIRS = [".git", "__pycache__", ".pytest_cache", ".gemini", "node_modules"]

def scan_repository(root_dir):
    results = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in EXTENSIONS:
                continue
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, root_dir)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                    for line_idx, line in enumerate(fp, 1):
                        for term in SEARCH_TERMS:
                            if term in line:
                                results.append({
                                    "file": rel_path,
                                    "line": line_idx,
                                    "term": term,
                                    "content": line.strip()[:160]
                                })
            except Exception as e:
                pass
    return pd.DataFrame(results)

if __name__ == "__main__":
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"Scanning workspace: {workspace_root} ...")
    df = scan_repository(workspace_root)
    out_path = os.path.join(workspace_root, "data", "phase7_3_5_number_search.csv")
    df.to_csv(out_path, index=False)
    print(f"Scan complete. Found {len(df)} occurrences. Saved to {out_path}")
    
    # Summary of occurrences by term
    print("\n=== SUMMARY BY TERM ===")
    print(df["term"].value_counts().to_string())
