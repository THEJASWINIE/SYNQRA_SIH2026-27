import os
import re
import json

patterns = [
    r'0\.085', r'0\.068', r'0\.10\b', r'\b20\b', r'\b42\b', r'\b43\b',
    r'38\.5\s*ms', r'end-to-end latency', r'worst-case command latency'
]
regex = re.compile('|'.join(patterns), re.IGNORECASE)

findings = []
for root, dirs, files in os.walk('.'):
    if any(p in root for p in ['.git', '.pytest_cache', '__pycache__', 'node_modules', '.venv', '.system_generated']):
        continue
    for file in files:
        if file.endswith(('.py', '.json', '.yaml', '.yml', '.ino', '.md')):
            path = os.path.join(root, file).replace('\\', '/')
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        m = regex.search(line)
                        if m:
                            findings.append({
                                'file': path,
                                'line': i,
                                'match': m.group(0),
                                'text': line.strip()[:120]
                            })
            except Exception:
                pass

print(f"Total scan matches found: {len(findings)}")

# Filter to key files (code and configs)
code_findings = [f for f in findings if f['file'].endswith(('.py', '.json', '.yaml', '.ino')) and not f['file'].startswith('./scratch/')]
print(f"Code/config matches: {len(code_findings)}")
for f in code_findings[:30]:
    print(f"  {f['file']}:{f['line']} [{f['match']}] -> {f['text'][:80]}")
