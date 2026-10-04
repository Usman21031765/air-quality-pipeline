import sqlite3

import pandas as pd

from etl.load import connect, upsert
from etl.transform import clean, to_dataframe
import run_pipeline


def sample_payload():
    return {
        "hourly": {
            "time": ["2026-10-01T00:00", "2026-10-01T01:00", "2026-10-01T01:00", "2026-10-01T02:00", "2026-10-01T03:00"],
            "pm10": [10.0, 12.0, 12.0, None, 5.0],
            "pm2_5": [8.0, 20.0, 20.0, None, -3.0],      # -3 is invalid
            "nitrogen_dioxide": [15.0, 18.0, 18.0, None, 9.0],
            "ozone": [60.0, 55.0, 55.0, None, 70.0],
        }
    }


def test_clean_removes_duplicates_and_empty_rows():
    df = clean(to_dataframe("Bristol", sample_payload()))
    assert len(df) == 3                      # duplicate hour + all-null hour removed
    assert df["time"].is_unique


def test_negative_values_become_null():
    df = clean(to_dataframe("Bristol", sample_payload()))
    assert pd.isna(df.loc[df["time"] == "2026-10-01T03:00:00Z", "pm2_5"]).all()


def test_who_flag():
    df = clean(to_dataframe("Bristol", sample_payload()))
    flags = dict(zip(df["time"], df["above_who_pm25"]))
    assert flags["2026-10-01T00:00:00Z"] == 0.0
    assert flags["2026-10-01T01:00:00Z"] == 1.0


def test_upsert_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "t.db"))
    df = clean(to_dataframe("Bristol", sample_payload()))
    upsert(conn, df)
    upsert(conn, df)                         # run twice
    assert conn.execute("SELECT COUNT(*) FROM air_quality").fetchone()[0] == 3


def test_one_failing_city_does_not_stop_others(tmp_path):
    def fake_fetch(city, lat, lon, **kwargs):
        if city == "London":
            raise RuntimeError("API down")
        return sample_payload()

    db = str(tmp_path / "t.db")
    failures = run_pipeline.run(db_path=db, fetch=fake_fetch)
    conn = sqlite3.connect(db)
    assert failures == 1
    cities = {r[0] for r in conn.execute("SELECT DISTINCT city FROM air_quality")}
    assert "London" not in cities and "Bristol" in cities
    assert conn.execute("SELECT COUNT(*) FROM pipeline_runs WHERE status='failed'").fetchone()[0] == 1
