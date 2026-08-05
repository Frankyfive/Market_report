#!/usr/bin/env python3
"""Pull the MBA Purchase Index Google Sheet and merge new weekly values into
data/manual/mba_manual.json, which extract_mba_csv.py then folds into the
cached CSV alongside the MBA_SEED history baked into index.html.
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request

SHEET_ID = "1tn8zNXHqHe8RmqX_s031AlxCMJfoKftrqK5Jokksoe8"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
index_path = os.path.join(repo_root, 'index.html')
manual_path = os.path.join(repo_root, 'data', 'manual', 'mba_manual.json')


def load_seed_dates():
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    m = re.search(r"const\s+MBA_SEED\s*=\s*(\[\s*\[.*?\]\s*\]);", html, re.S)
    if not m:
        print('MBA_SEED not found in index.html', file=sys.stderr)
        sys.exit(2)
    seed = json.loads(m.group(1).replace("'", '"'))
    return {d for d, _ in seed}


def load_manual():
    if os.path.exists(manual_path):
        with open(manual_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def fetch_sheet_rows():
    req = urllib.request.Request(SHEET_CSV_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode('utf-8')
    reader = csv.reader(io.StringIO(text))
    rows = []
    next(reader, None)  # header row
    for row in reader:
        if len(row) < 2:
            continue
        date, val = row[0].strip(), row[1].strip()
        if not date or not val:
            continue
        try:
            rows.append((date, float(val)))
        except ValueError:
            continue
    return rows


def parse_date_key(s):
    m, d, y = s.split('/')
    return (int(y), int(m), int(d))


def main():
    seed_dates = load_seed_dates()
    manual = load_manual()
    manual_map = {item['date']: item for item in manual}

    sheet_rows = fetch_sheet_rows()
    added, updated = [], []
    for date, val in sheet_rows:
        if date in seed_dates:
            continue  # already part of the baked-in history
        existing = manual_map.get(date)
        if existing is None:
            manual_map[date] = {'date': date, 'val': val}
            added.append((date, val))
        elif existing['val'] != val:
            existing['val'] = val
            updated.append((date, val))

    if not added and not updated:
        print('No new MBA values found in the sheet.')
        return

    merged = sorted(manual_map.values(), key=lambda r: parse_date_key(r['date']))
    os.makedirs(os.path.dirname(manual_path), exist_ok=True)
    with open(manual_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2)
        f.write('\n')

    for date, val in added:
        print(f'Added {date}: {val}')
    for date, val in updated:
        print(f'Updated {date}: {val}')


if __name__ == '__main__':
    main()
