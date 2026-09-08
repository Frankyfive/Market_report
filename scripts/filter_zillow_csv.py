#!/usr/bin/env python3
"""Trim a Zillow metro-level research CSV to the rows the dashboard actually uses.

Zillow publishes one row per metro (900ish rows, several MB). The dashboard only
charts the national row plus eight target metros, so keeping the full file just
makes the browser download megabytes it throws away. Reads the CSV at `path` and
rewrites it in place with the header, the `country` row, and the target metros.
"""
import csv
import sys

TARGET_METROS = {
    ('Dallas, TX', 'TX'),
    ('Houston, TX', 'TX'),
    ('Denver, CO', 'CO'),
    ('San Antonio, TX', 'TX'),
    ('Austin, TX', 'TX'),
    ('El Paso, TX', 'TX'),
    ('Colorado Springs, CO', 'CO'),
    ('McAllen, TX', 'TX'),
}


def keep(row):
    if row.get('RegionType') == 'country':
        return True
    return (row.get('RegionName'), row.get('StateName')) in TARGET_METROS


def filter_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = [r for r in reader if keep(r)]
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print('%s: kept %d rows' % (p, filter_csv(p)))
