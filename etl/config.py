"""Central settings for the pipeline."""

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
DB_PATH = "data/air_quality.db"

# city -> (latitude, longitude)
CITIES = {
    "Bristol": (51.4545, -2.5879),
    "London": (51.5072, -0.1276),
    "Manchester": (53.4808, -2.2426),
    "Birmingham": (52.4862, -1.8904),
    "Leeds": (53.8008, -1.5491),
}

POLLUTANTS = ["pm10", "pm2_5", "nitrogen_dioxide", "ozone"]

# Values outside this range are treated as sensor/API errors (ug/m3)
VALID_RANGE = (0, 1000)

# WHO 2021 24-hour guideline for PM2.5 (ug/m3), used as a simple indicator
WHO_PM25_GUIDELINE = 15
