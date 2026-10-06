"""Record when each dashboard data source was last refreshed in data/update_log.json.

Usage:
  python3 scripts/update_log.py realtor fred   # stamp these sources as updated now
  python3 scripts/update_log.py --seed         # stamp every source from its last git commit

"Data through" is recomputed for every source on each run from the cached files,
so the log always reflects the latest period actually on disk.
"""

import argparse
import csv
import json
import os
import subprocess
from datetime import datetime, timezone

LOG_PATH = "data/update_log.json"

# Files each source writes; used for --seed.
SOURCE_PATHS = {
    "realtor": ["data/cache/us_history.csv", "data/cache/state_history.csv", "data/cache/metro_history.csv", "data/cache/weekly_inventory.csv"],
    "fred": ["data/cache/fred"],
    "zillow": ["data/cache/zillow"],
    "redfin": ["data/manual/rf_tracker.json", "data/manual/redfin_cancel.json"],
    "mba": ["data/manual/mba_manual.json", "data/cache/mba_purchase_index.csv"],
    "tamu": ["data/manual/tamu_housing.json"],
}


def realtor_through():
    with open("data/cache/us_history.csv", newline="") as f:
        months = [r["month_date_yyyymm"] for r in csv.DictReader(f) if r.get("month_date_yyyymm", "").isdigit()]
    m = max(months)
    return f"{m[:4]}-{m[4:6]}"


def fred_through():
    with open("data/cache/fred/MORTGAGE30US.json") as f:
        return max(o["date"] for o in json.load(f))


def zillow_through():
    with open("data/cache/zillow/zhvi.csv", newline="") as f:
        monthly = next(csv.reader(f))[-1]
    with open("data/cache/zillow/inventory_weekly.csv", newline="") as f:
        weekly = next(csv.reader(f))[-1]
    return f"{monthly[:7]} (monthly), {weekly} (weekly)"


def redfin_through():
    with open("data/manual/rf_tracker.json") as f:
        housing = max(r["period"] for r in json.load(f)["housing"])
    return housing[:7]


def mba_through():
    with open("data/cache/mba_purchase_index.csv", newline="") as f:
        dates = [datetime.strptime(r["date"], "%m/%d/%Y") for r in csv.DictReader(f)]
    return max(dates).strftime("%Y-%m-%d")


def tamu_through():
    with open("data/manual/tamu_housing.json") as f:
        return max(r["date"] for r in json.load(f))[:7]


THROUGH = {
    "realtor": realtor_through,
    "fred": fred_through,
    "zillow": zillow_through,
    "redfin": redfin_through,
    "mba": mba_through,
    "tamu": tamu_through,
}


def git_last_commit(paths):
    out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", *paths],
                         capture_output=True, text=True, check=True).stdout.strip()
    if not out:
        return None
    return datetime.fromisoformat(out).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources", nargs="*", help=f"sources refreshed in this run: {', '.join(THROUGH)}")
    ap.add_argument("--seed", action="store_true", help="stamp every source from git history")
    args = ap.parse_args()
    unknown = set(args.sources) - set(THROUGH)
    if unknown:
        ap.error(f"unknown source(s): {', '.join(sorted(unknown))}")

    try:
        with open(LOG_PATH) as f:
            log = json.load(f)
    except FileNotFoundError:
        log = {}
    sources = log.setdefault("sources", {})

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for key, through_fn in THROUGH.items():
        entry = sources.setdefault(key, {})
        if args.seed:
            entry["updated"] = git_last_commit(SOURCE_PATHS[key]) or entry.get("updated")
        if key in args.sources:
            entry["updated"] = now
        try:
            entry["data_through"] = through_fn()
        except (OSError, KeyError, ValueError, StopIteration) as e:
            print(f"{key}: could not read data-through date ({e})")

    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)
        f.write("\n")
    for key, entry in sources.items():
        print(f"{key:8} updated {entry.get('updated')}  data through {entry.get('data_through')}")


if __name__ == "__main__":
    main()
