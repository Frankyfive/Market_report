Data pulled from public websites for housing.

## Sources

| Source | Data | Refresh |
|---|---|---|
| [Realtor.com](https://www.realtor.com/research/data/) | National / state / metro inventory metrics | Automated, Mondays 06:00 UTC |
| [Zillow Research](https://www.zillow.com/research/data/) | Inventory, sales, values, rents, affordability | Automated, Mondays 07:00 UTC |
| [Redfin Data Center](https://www.redfin.com/news/data-center/downloads/) | Housing market, buyers/sellers, delistings, cancellations | Automated, Mondays 08:00 UTC |
| [FRED](https://fred.stlouisfed.org/) | Economic indicators | Automated with Realtor.com |
| [Texas A&M TRERC](https://trerc.tamu.edu/) | Texas housing | Manual CSV upload |
| MBA Purchase Index | Weekly applications | Manual entry / Google Sheet sync |

## How the automation works

Each source has a GitHub Actions workflow in [.github/workflows](.github/workflows) that
downloads the raw files, trims them to what the dashboard renders, and commits the result
under `data/`. The page then reads those cached files instead of hitting the sources live.

- **Redfin** ([cache-redfin.yml](.github/workflows/cache-redfin.yml)) pulls the same CSVs the
  Data Center download buttons serve, from `redfin-public-data.s3.us-west-2.amazonaws.com/redfin_data_center`,
  and [scripts/build_redfin_json.py](scripts/build_redfin_json.py) converts them into the JSON
  the page loads. The CSV upload buttons in the UI still work and merge with the cached data —
  use them only to pull a release in early or to add history beyond the cached window.
- **Zillow** ([cache-zillow.yml](.github/workflows/cache-zillow.yml)) downloads the metro-level
  research CSVs, then [scripts/filter_zillow_csv.py](scripts/filter_zillow_csv.py) trims each to
  the national row plus the eight target metros (~21 MB down to ~800 KB).
- **Realtor.com** ([cache-csvs.yml](.github/workflows/cache-csvs.yml)) caches the country and
  state histories in full and filters the metro history to the target CBSA codes.

Changing the tracked metros means updating the CBSA list in `cache-csvs.yml`, `TARGET_METROS`
and `ZILLOW_REGION_MAP` in `index.html`, and `TARGET_METROS` in `filter_zillow_csv.py`.
