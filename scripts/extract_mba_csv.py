#!/usr/bin/env python3
import re, json, csv, os, sys
from datetime import datetime

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
index_path = os.path.join(repo_root, 'index.html')
manual_path = os.path.join(repo_root, 'data', 'manual', 'mba_manual.json')
out_path = os.path.join(repo_root, 'data', 'cache', 'mba_purchase_index.csv')

with open(index_path, 'r', encoding='utf-8') as f:
    html = f.read()

m = re.search(r"const\s+MBA_SEED\s*=\s*(\[\s*\[.*?\]\s*\]);", html, re.S)
if not m:
    print('MBA_SEED not found in index.html', file=sys.stderr)
    sys.exit(2)
seed_text = m.group(1)
# convert JS-style array with single quotes to JSON
seed_json = seed_text.replace("'", '"')
try:
    seed = json.loads(seed_json)
except Exception as e:
    print('Failed to parse MBA_SEED:', e, file=sys.stderr)
    sys.exit(3)

manual = []
if os.path.exists(manual_path):
    with open(manual_path, 'r', encoding='utf-8') as f:
        manual = json.load(f)

# Build map and overlay manual
mmap = {}
for d, v in seed:
    mmap[d] = {'date': d, 'val': float(v), 'manual': False}
for item in manual:
    d = item['date']
    v = float(item['val'])
    mmap[d] = {'date': d, 'val': v, 'manual': True}

# sort by parsed date
def parse_date(s):
    try:
        return datetime.strptime(s, '%m/%d/%Y')
    except Exception:
        # try other formats
        try:
            return datetime.strptime(s, '%m/%d/%y')
        except Exception:
            return None

rows = list(mmap.values())
rows = [r for r in rows if parse_date(r['date']) is not None]
rows.sort(key=lambda r: parse_date(r['date']))

os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['date', 'value', 'manual'])
    for r in rows:
        w.writerow([r['date'], ('%.1f' % r['val']).rstrip('0').rstrip('.') if isinstance(r['val'], float) else r['val'], 'yes' if r['manual'] else 'no'])

print('Wrote', out_path)
