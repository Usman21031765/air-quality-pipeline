"""Run the full pipeline: extract -> transform -> load, for every city.

Loads into Azure SQL Database when AZURE_SQL_SERVER is set (GitHub Actions),
otherwise into a local SQLite file (local runs and tests).
"""
import argparse
import logging
import os
import sys

from etl.config import CITIES, DB_PATH
from etl.extract import fetch_city
from etl.transform import clean, to_dataframe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pipeline")


def get_loader():
    if os.getenv("AZURE_SQL_SERVER"):
        from etl import load_azure
        log.info("Target: Azure SQL Database")
        return load_azure
    from etl import load
    log.info("Target: local SQLite")
    return load


def run(db_path=DB_PATH, fetch=fetch_city, past_days=2, loader=None):
    loader = loader or get_loader()
    conn = loader.connect(db_path)
    failures = 0
    for city, (lat, lon) in CITIES.items():
        try:
            payload = fetch(city, lat, lon, past_days=past_days)
            raw = to_dataframe(city, payload)
            df = clean(raw)
            loaded = loader.upsert(conn, df)
            loader.log_run(conn, city, len(raw), loaded, "success")
            log.info("%s: fetched %d, loaded %d rows", city, len(raw), loaded)
        except Exception as exc:  # one city failing must not stop the others
            failures += 1
            loader.log_run(conn, city, None, None, "failed", str(exc))
            log.error("%s: FAILED - %s", city, exc)
    conn.close()
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--past-days", type=int, default=2,
                        help="days of history to fetch (use a large number for a one-off backfill)")
    args = parser.parse_args()
    sys.exit(1 if run(past_days=args.past_days) else 0)
