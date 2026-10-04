"""EXTRACT: pull hourly air-quality data for one city from the Open-Meteo API."""
import logging
import time

import requests

from etl.config import API_URL, POLLUTANTS

log = logging.getLogger(__name__)


def fetch_city(city, lat, lon, past_days=2, retries=3, backoff=2.0):
    """Return the raw JSON payload for a city. Retries on network errors."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(POLLUTANTS),
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": "UTC",
    }
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            if "hourly" not in payload:
                raise ValueError(f"No 'hourly' data in response for {city}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            log.warning("%s: attempt %d/%d failed: %s", city, attempt, retries, exc)
            if attempt == retries:
                raise
            time.sleep(backoff ** attempt)
