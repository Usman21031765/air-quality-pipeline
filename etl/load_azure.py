"""LOAD (Azure): write clean rows into Azure SQL Database using MERGE (an upsert).

Connection details come from environment variables (GitHub Actions secrets),
never from the code, because this repository is public.
"""
import logging
import os
import time
from datetime import datetime, timezone

from etl.config import POLLUTANTS

log = logging.getLogger(__name__)

COLS = ["city", "time", *POLLUTANTS, "above_who_pm25"]

CREATE_AIR_QUALITY = """
IF OBJECT_ID('dbo.air_quality', 'U') IS NULL
CREATE TABLE dbo.air_quality (
    city             NVARCHAR(50)  NOT NULL,
    [time]           DATETIME2(0)  NOT NULL,
    pm10             FLOAT         NULL,
    pm2_5            FLOAT         NULL,
    nitrogen_dioxide FLOAT         NULL,
    ozone            FLOAT         NULL,
    above_who_pm25   TINYINT       NULL,
    loaded_at        DATETIME2(0)  NOT NULL,
    CONSTRAINT pk_air_quality PRIMARY KEY (city, [time])
)
"""

CREATE_RUNS = """
IF OBJECT_ID('dbo.pipeline_runs', 'U') IS NULL
CREATE TABLE dbo.pipeline_runs (
    run_at       DATETIME2(0)   NOT NULL,
    city         NVARCHAR(50)   NOT NULL,
    rows_fetched INT            NULL,
    rows_loaded  INT            NULL,
    status       NVARCHAR(20)   NOT NULL,
    error        NVARCHAR(1000) NULL
)
"""

# T-SQL has no "ON CONFLICT", so an upsert is written with MERGE.
MERGE_SQL = """
MERGE dbo.air_quality AS t
USING (SELECT %s AS city, CAST(%s AS DATETIME2(0)) AS [time], %s AS pm10, %s AS pm2_5,
              %s AS nitrogen_dioxide, %s AS ozone, %s AS above_who_pm25,
              CAST(%s AS DATETIME2(0)) AS loaded_at) AS s
ON t.city = s.city AND t.[time] = s.[time]
WHEN MATCHED THEN UPDATE SET
    pm10 = s.pm10, pm2_5 = s.pm2_5, nitrogen_dioxide = s.nitrogen_dioxide,
    ozone = s.ozone, above_who_pm25 = s.above_who_pm25, loaded_at = s.loaded_at
WHEN NOT MATCHED THEN INSERT
    (city, [time], pm10, pm2_5, nitrogen_dioxide, ozone, above_who_pm25, loaded_at)
    VALUES (s.city, s.[time], s.pm10, s.pm2_5, s.nitrogen_dioxide, s.ozone,
            s.above_who_pm25, s.loaded_at);
"""


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def connect(db_path=None, attempts=5, wait=20):
    """Connect to Azure SQL. The free serverless database auto-pauses when idle,
    so the first connection can fail while it wakes up - hence the retries."""
    import pymssql  # imported here so tests can run without the package installed

    for attempt in range(1, attempts + 1):
        try:
            conn = pymssql.connect(
                server=os.environ["AZURE_SQL_SERVER"],
                user=os.environ["AZURE_SQL_USER"],
                password=os.environ["AZURE_SQL_PASSWORD"],
                database=os.environ["AZURE_SQL_DATABASE"],
                login_timeout=60,
                timeout=120,
            )
            cur = conn.cursor()
            cur.execute(CREATE_AIR_QUALITY)
            cur.execute(CREATE_RUNS)
            conn.commit()
            return conn
        except Exception as exc:
            log.warning("Azure SQL connect attempt %d/%d failed: %s", attempt, attempts, exc)
            if attempt == attempts:
                raise
            time.sleep(wait)


def upsert(conn, df):
    """Insert new rows and update existing ones. Safe to re-run."""
    if df.empty:
        return 0
    loaded_at = _now()
    rows = []
    for rec in df[COLS].itertuples(index=False):
        city, ts, *values, flag = rec
        values = [None if v != v else float(v) for v in values]   # NaN -> NULL
        flag = None if flag != flag else int(flag)
        rows.append((city, datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"), *values, flag, loaded_at))
    cur = conn.cursor()
    cur.executemany(MERGE_SQL, rows)
    conn.commit()
    return len(rows)


def log_run(conn, city, fetched, loaded, status, error=None):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO dbo.pipeline_runs (run_at, city, rows_fetched, rows_loaded, status, error) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (_now(), city, fetched, loaded, status, (error or None) and error[:1000]),
    )
    conn.commit()
