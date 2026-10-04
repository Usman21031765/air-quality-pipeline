import pandas as pd

from etl import load_azure
from etl.transform import clean, to_dataframe


class FakeCursor:
    def __init__(self):
        self.calls = []

    def executemany(self, sql, rows):
        self.calls.append((sql, list(rows)))


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1


def sample_df():
    payload = {"hourly": {
        "time": ["2026-10-01T00:00", "2026-10-01T01:00"],
        "pm10": [10.0, None], "pm2_5": [8.0, 20.0],
        "nitrogen_dioxide": [15.0, None], "ozone": [60.0, 55.0],
    }}
    return clean(to_dataframe("Bristol", payload))


def test_azure_upsert_builds_merge_rows():
    conn = FakeConn()
    n = load_azure.upsert(conn, sample_df())
    sql, rows = conn.cur.calls[0]
    assert n == 2 and len(rows) == 2
    assert "MERGE" in sql and "WHEN NOT MATCHED" in sql
    first, second = rows
    assert first[0] == "Bristol" and first[1].year == 2026
    assert second[2] is None                  # NaN pm10 became NULL
    assert first[6] == 0 and second[6] == 1   # WHO flag stored as 0 / 1
    assert conn.commits == 1


def test_azure_upsert_empty_dataframe():
    assert load_azure.upsert(FakeConn(), pd.DataFrame()) == 0
