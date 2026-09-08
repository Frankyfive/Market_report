#!/usr/bin/env python3
"""Turn Redfin Data Center CSVs into the JSON files the dashboard loads.

Redfin publishes its Data Center datasets as plain CSVs on a public S3 bucket
(the same files the website's Download buttons hand you), so the manual
download-and-upload loop can run unattended. This script is the automated
equivalent of a person downloading those CSVs and clicking Upload: it emits row
shapes identical to the browser's upload path, including the `key` field the
dashboard dedupes on, so repo-loaded and hand-uploaded rows merge cleanly.

Usage:
    python scripts/build_redfin_json.py [--src DIR] [--out DIR]

Reads the CSVs from --src (default: a temp dir the workflow fills) and writes
data/manual/rf_tracker.json and data/manual/redfin_cancel.json.
"""
import argparse
import csv
import io
import json
import os
import sys
from datetime import date

# The cancellations file covers ~950 metros back to 2012. The dashboard only
# ever renders the latest period (rankings) and the last 24 periods (charts),
# so keeping the whole thing would mean shipping tens of megabytes nobody
# reads. The state/region files are small enough to keep in full.
CANCEL_RETAIN_MONTHS = 36
TRACKER_RETAIN_MONTHS = 0  # 0 = keep everything

SOURCES = {
    'housing': 'housing_market/monthly/all_states.csv',
    'buyers': 'buyers_and_sellers/monthly/all_census_regions.csv',
    'delist': 'delistings_relistings/monthly/all_states.csv',
    'cancel': 'contract_cancellations/monthly/all_metros.csv',
}


def local_name(s3_path):
    """The flat filename the workflow saves an S3 path under."""
    return s3_path.replace('/', '_')


def pf(v):
    """Parse a Redfin numeric cell. Mirrors the `pf` helper in index.html."""
    if v is None:
        return None
    v = v.strip()
    if v == '' or v == 'NA':
        return None
    try:
        return float(v.replace(',', ''))
    except ValueError:
        return None


def read_rows(src_dir, s3_path):
    path = os.path.join(src_dir, local_name(s3_path))
    if not os.path.exists(path):
        raise SystemExit('missing input: %s' % path)
    with io.open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def cutoff(months):
    """The earliest PERIOD BEGIN to keep, as a 'YYYY-MM-DD' string."""
    if not months:
        return None
    today = date.today()
    total = today.year * 12 + (today.month - 1) - months
    return '%04d-%02d-01' % (total // 12, total % 12 + 1)


def recent(rows, months):
    floor = cutoff(months)
    if not floor:
        return rows
    return [r for r in rows if (r.get('PERIOD BEGIN') or '') >= floor]


def tracker_key(row):
    return '%s|%s|%s' % (row['REGION NAME'], row['PERIOD BEGIN'], row.get('PROPERTY TYPE') or '')


def build_housing(rows):
    out = []
    for r in rows:
        if not r.get('REGION NAME') or not r.get('PERIOD BEGIN'):
            continue
        out.append({
            'key': tracker_key(r),
            'region': r['REGION NAME'],
            'period': r['PERIOD BEGIN'],
            'regionType': r.get('REGION TYPE'),
            'homesSold': pf(r.get('HOMES SOLD')),
            'homesSoldYoy': pf(r.get('HOMES SOLD YOY (%)')),
            'pendingSales': pf(r.get('PENDING SALES')),
            'pendingYoy': pf(r.get('PENDING SALES YOY (%)')),
            'medPrice': pf(r.get('MEDIAN SALE PRICE NSA ($)')),
            'medPriceYoy': pf(r.get('MEDIAN SALE PRICE NSA YOY (%)')),
            'newListings': pf(r.get('NEW LISTINGS')),
            'newListingsYoy': pf(r.get('NEW LISTINGS YOY (%)')),
            'active': pf(r.get('ACTIVE LISTINGS')),
            'activeYoy': pf(r.get('ACTIVE LISTINGS YOY (%)')),
            'dom': pf(r.get('MEDIAN DAYS ON MARKET (DAYS)')),
            'domYoy': pf(r.get('MEDIAN DAYS ON MARKET YOY (%)')),
        })
    return out


def build_buyers(rows):
    out = []
    for r in rows:
        if not r.get('REGION NAME') or not r.get('PERIOD BEGIN'):
            continue
        out.append({
            'key': tracker_key(r),
            'region': r['REGION NAME'],
            'period': r['PERIOD BEGIN'],
            'propType': r.get('PROPERTY TYPE') or 'All Residential',
            'balance': r.get('BALANCE OF POWER') or '',
            'buyers': pf(r.get('BUYERS')),
            'buyersYoy': pf(r.get('BUYERS YOY (%)')),
            'sellers': pf(r.get('SELLERS')),
            'sellersYoy': pf(r.get('SELLERS YOY (%)')),
            'bsRatio': pf(r.get('BUYER-SELLER RATIO')),
            'bsRatioYoy': pf(r.get('BUYER-SELLER RATIO YOY (%)')),
            'sbDiff': pf(r.get('SELLER-BUYER % DIFFERENCE')),
            'sbDiffYoy': pf(r.get('SELLER-BUYER % DIFFERENCE YOY (PPTS)')),
        })
    return out


def build_delist(rows):
    out = []
    for r in rows:
        if not r.get('REGION NAME') or not r.get('PERIOD BEGIN'):
            continue
        out.append({
            'key': tracker_key(r),
            'region': r['REGION NAME'],
            'period': r['PERIOD BEGIN'],
            'regionType': r.get('REGION TYPE'),
            'delistings': pf(r.get('TOTAL DELISTINGS')),
            'delistYoy': pf(r.get('TOTAL DELISTINGS YOY (%)')),
            'relistings': pf(r.get('TOTAL RELISTINGS')),
            'relistYoy': pf(r.get('TOTAL RELISTINGS YOY (%)')),
            'delistShare': pf(r.get('SHARE OF LISTINGS DELISTED (%)')),
            'delistShareYoy': pf(r.get('SHARE OF LISTINGS DELISTED YOY (PPTS)')),
            'relistShare': pf(r.get('SHARE OF LISTINGS RELISTED (%)')),
            'relistShareYoy': pf(r.get('SHARE OF LISTINGS RELISTED YOY (PPTS)')),
        })
    return out


def build_cancel(rows):
    # Note the two-part key here: the upload path in index.html keys
    # cancellations on region|period, without the property-type segment.
    out = []
    for r in rows:
        if not r.get('REGION NAME') or not r.get('PERIOD BEGIN'):
            continue
        out.append({
            'key': '%s|%s' % (r['REGION NAME'], r['PERIOD BEGIN']),
            'region': r['REGION NAME'],
            'period': r['PERIOD BEGIN'],
            'cancellations': pf(r.get('HOME PURCHASE CANCELLATIONS')) or 0,
            'cancelMom': pf(r.get('HOME PURCHASE CANCELLATIONS MOM (%)')),
            'cancelYoy': pf(r.get('HOME PURCHASE CANCELLATIONS YOY (%)')),
            'pctPending': pf(r.get('PERCENT OF PENDING SALES (%)')),
            'pctMom': pf(r.get('PERCENT OF PENDING SALES MOM (PPTS)')),
            'pctYoy': pf(r.get('PERCENT OF PENDING SALES YOY (PPTS)')),
        })
    return out


def write_json(path, payload, label):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(payload, fh, separators=(',', ':'))
    size = os.path.getsize(path) / 1024.0 / 1024.0
    print('  wrote %-34s %7.2f MB  %s' % (os.path.basename(path), size, label))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='redfin_src', help='directory holding the downloaded CSVs')
    ap.add_argument('--out', default='data/manual', help='directory to write the JSON into')
    args = ap.parse_args()

    housing = build_housing(recent(read_rows(args.src, SOURCES['housing']), TRACKER_RETAIN_MONTHS))
    buyers = build_buyers(recent(read_rows(args.src, SOURCES['buyers']), TRACKER_RETAIN_MONTHS))
    delist = build_delist(recent(read_rows(args.src, SOURCES['delist']), TRACKER_RETAIN_MONTHS))
    cancel = build_cancel(recent(read_rows(args.src, SOURCES['cancel']), CANCEL_RETAIN_MONTHS))

    for name, rows in [('housing', housing), ('buyers', buyers), ('delist', delist), ('cancel', cancel)]:
        if not rows:
            raise SystemExit('refusing to write: %s produced no rows' % name)

    latest = max(r['period'] for r in housing)
    print('Redfin latest period: %s' % latest)

    if not os.path.isdir(args.out):
        os.makedirs(args.out)
    write_json(os.path.join(args.out, 'rf_tracker.json'),
               {'housing': housing, 'buyers': buyers, 'delist': delist},
               '%d housing / %d buyers / %d delist rows' % (len(housing), len(buyers), len(delist)))
    write_json(os.path.join(args.out, 'redfin_cancel.json'), cancel,
               '%d rows, last %d months' % (len(cancel), CANCEL_RETAIN_MONTHS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
