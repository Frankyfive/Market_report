"""Fetch Texas A&M TRERC housing activity and merge it into data/manual/tamu_housing.json.

The trerc.tamu.edu housing-activity page fills its table and CSV button from a JSON
endpoint; this calls the same endpoint for each tracked market. TRERC revises recent
months, so fetched rows replace any existing row with the same market and month.
"""

import argparse
import json
import sys
import time
import urllib.request

TABLE_URL = "https://trerc.tamu.edu/wp-json/trerc-data/v1/housing-activity-table"
# Cloudflare in front of trerc.tamu.edu rejects urllib's default user agent.
USER_AGENT = "Mozilla/5.0 (compatible; Market_report/1.0; +https://github.com/Frankyfive/Market_report)"

# geoId values come from https://trerc.tamu.edu/wp-json/trerc-data/v1/housing-activity?selects
MARKETS = [
    {"geoId": "26", "geoName": "Texas", "geoTypeId": 1, "geoType": "State", "hashKey": "State"},
    {"geoId": "3", "geoName": "Austin-Round Rock-San Marcos", "geoTypeId": 2, "geoType": "Metropolitan Statistical Area", "hashKey": "MSA"},
    {"geoId": "8", "geoName": "Dallas-Fort Worth-Arlington", "geoTypeId": 2, "geoType": "Metropolitan Statistical Area", "hashKey": "MSA"},
    {"geoId": "9", "geoName": "El Paso", "geoTypeId": 2, "geoType": "Metropolitan Statistical Area", "hashKey": "MSA"},
    {"geoId": "10", "geoName": "Houston-Pasadena-The Woodlands", "geoTypeId": 2, "geoType": "Metropolitan Statistical Area", "hashKey": "MSA"},
    {"geoId": "19", "geoName": "San Antonio-New Braunfels", "geoTypeId": 2, "geoType": "Metropolitan Statistical Area", "hashKey": "MSA"},
]


def fetch_market(geo):
    body = json.dumps({"geoData": geo, "tableTypes": {"period": "monthly"}}).encode()
    req = urllib.request.Request(TABLE_URL, data=body, method="POST", headers={
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": USER_AGENT,
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    # The endpoint returns a JSON string that itself holds the JSON object.
    if isinstance(payload, str):
        payload = json.loads(payload)
    if payload.get("status") != "success":
        raise RuntimeError(f"{geo['geoName']}: status {payload.get('status')!r}")
    return payload["rowData"]


def pct(v):
    # API reports percents (5.98); the dashboard stores fractions (0.0598).
    return round(v / 100, 6) if v else None


def to_row(r):
    market, date = r["data_market_name"], r["begin_date"]
    return {
        "key": f"{market}|{date}",
        "market": market,
        "date": date,
        "sales": int(r["closed_listings"] or 0),
        "salesYoy": pct(r["closed_listings_yoy_pct"]),
        "dollarVol": int(r["dollar_volume"] or 0),
        "dollarVolYoy": pct(r["dollar_volume_yoy_pct"]),
        "avgPrice": int(r["avg_close_price"] or 0),
        "medPrice": int(r["median_close_price"] or 0),
        "activeListings": int(r["active_listings"] or 0),
        "monthsInv": float(r["months_inventory"] or 0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/manual/tamu_housing.json")
    args = ap.parse_args()

    try:
        with open(args.out, encoding="utf-8") as f:
            existing = {r["key"]: r for r in json.load(f)}
    except FileNotFoundError:
        existing = {}

    before = len(existing)
    for geo in MARKETS:
        rows = [to_row(r) for r in fetch_market(geo)]
        if not rows:
            raise RuntimeError(f"{geo['geoName']}: no rows returned")
        for row in rows:
            existing[row["key"]] = row
        print(f"{geo['geoName']}: {len(rows)} months, latest {max(r['date'] for r in rows)}")
        time.sleep(2)

    merged = sorted(existing.values(), key=lambda r: (r["market"], r["date"]), reverse=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, separators=(",", ":"))
    print(f"Wrote {len(merged)} rows ({len(merged) - before:+d}) to {args.out}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"TAMU fetch failed: {e}", file=sys.stderr)
        sys.exit(1)
