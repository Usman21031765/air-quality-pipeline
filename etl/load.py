"""LOAD: write clean rows into SQLite using an idempotent upsert."""
import sqlite3
from datetime import datetime, timezone

from etl.config import DB_PATH, POLLUTANTS

SCHEMA = """
CREATE TABLE IF NOT EXISTS air_quality (
    city             TEXT NOT NULL,
    time             TEXT NOT NULL,
    pm10             REAL,
    pm2_5            REAL,
    nitrogen_dioxide REAL,
    ozone            REAL,
    above_who_pm25   INTEGER,
    loaded_at        TEXT NOT NULL,
    PRIMARY KEY (city, time)
);
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_at       TEXT NOT NULL,
    city         TEXT NOT NULL,
    rows_fetched INTEGER,
    rows_loaded  INTEGER,
    status       TEXT NOT NULL,
    error        TEXT
);
"""

COLS = ["city", "time", *POLLUTANTS, "above_who_pm25"]


def connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upsert(conn, df):
    """Insert new rows, update existing ones. Safe to re-run any number of times."""
    if df.empty:
        return 0
    rows = df[COLS].astype(object).where(df[COLS].notna(), None).values.tolist()
    loaded_at = _now()
    rows = [(*r[:-1], None if r[-1] is None else int(r[-1]), loaded_at) for r in rows]
    sql = f"""
        INSERT INTO air_quality ({', '.join(COLS)}, loaded_at)
        VALUES ({', '.join('?' * (len(COLS) + 1))})
        ON CONFLICT(city, time) DO UPDATE SET
            {', '.join(f'{c}=excluded.{c}' for c in POLLUTANTS + ['above_who_pm25', 'loaded_at'])}
    """
    with conn:
        conn.executemany(sql, rows)
    return len(rows)


def log_run(conn, city, fetched, loaded, status, error=None):
    with conn:
        conn.execute(
            "INSERT INTO pipeline_runs VALUES (?,?,?,?,?,?)",
            (_now(), city, fetched, loaded, status, error),
        )
