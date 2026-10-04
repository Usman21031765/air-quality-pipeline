"""TRANSFORM: turn the raw JSON into a clean, validated DataFrame."""
import numpy as np
import pandas as pd

from etl.config import POLLUTANTS, VALID_RANGE, WHO_PM25_GUIDELINE


def to_dataframe(city, payload):
    df = pd.DataFrame(payload["hourly"])
    df.insert(0, "city", city)
    return df


def clean(df):
    """Validate and standardise. Returns a new DataFrame."""
    df = df.copy()

    # 1. Consistent timestamps (UTC, ISO-8601 text)
    df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
    df = df.dropna(subset=["time"])
    df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Make sure every pollutant column exists and is numeric
    for col in POLLUTANTS:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 3. Out-of-range values are treated as errors, not real readings
    low, high = VALID_RANGE
    for col in POLLUTANTS:
        df.loc[(df[col] < low) | (df[col] > high), col] = np.nan

    # 4. Drop rows with no usable measurement, and duplicate city/hour rows
    df = df.dropna(subset=POLLUTANTS, how="all")
    df = df.drop_duplicates(subset=["city", "time"], keep="last")

    # 5. Simple derived indicator: hour above the WHO PM2.5 guideline
    df["above_who_pm25"] = np.where(
        df["pm2_5"].isna(), np.nan, (df["pm2_5"] > WHO_PM25_GUIDELINE).astype(float)
    )
    return df.reset_index(drop=True)
