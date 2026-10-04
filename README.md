# UK Air Quality Data Pipeline

An automated ETL pipeline that collects hourly air-quality data for five UK cities, cleans and
validates it, and loads it into Azure SQL Database for analysis. A scheduled GitHub Actions
workflow runs it every day, so the dataset keeps growing without manual work.

**Business question:** How does air quality in Bristol compare with other major UK cities?

**Tech stack:** Python (pandas, requests, pymssql), SQL (Azure SQL Database in production,
SQLite locally), pytest, GitHub Actions

## Key findings

Based on about 2,160 hourly readings per city (6 July to 3 October 2026, forecast hours excluded):

| City | Average PM2.5 (ug/m3) | Hours above WHO guideline |
|---|---|---|
| London | 6.3 | (from query) % |
| Manchester | 5.9 | (from query) % |
| **Bristol** | **5.6** | (from query) % |
| Birmingham | 5.5 | (from query) % |
| Leeds | 5.3 | (from query) % |

- London had the highest average PM2.5, and Bristol ranked third of five.
- All five cities averaged well below the WHO 24-hour guideline of 15 ug/m3.
- Differences between cities are small, and the window covers only about three months of summer
  and autumn, so this is a snapshot and not a full-year picture.
- Modelled NO2 follows a daily cycle: roughly 13 ug/m3 around 07:00 UTC and again late evening,
  and about 5 ug/m3 in the early afternoon. Because the data is modelled at about 11 km resolution,
  this shows the regional pattern and not street-level traffic effects.

## Dashboard

A Power BI report built on the Azure database, with DAX measures, a city selector and a date range.

![Power BI dashboard](dashboard/dashboard.png)

A PDF version is in [`dashboard/air_quality_dashboard.pdf`](dashboard/air_quality_dashboard.pdf).
The dashboard is a snapshot of the data at export time, because it reads Azure in Import mode.

## How it works

```
Open-Meteo Air Quality API --> extract.py --> transform.py --> load_azure.py --> Azure SQL Database
      (hourly JSON)            fetch + retry   clean + validate  MERGE upsert      air_quality
                                                                                   pipeline_runs
                                       ^
                        GitHub Actions: run tests, then the pipeline, every day
```

- **Extract:** requests hourly PM10, PM2.5, nitrogen dioxide and ozone for each city, with
  timeouts and automatic retries.
- **Transform:** standardises timestamps to UTC, forces numeric types, sets impossible values
  (negative or above 1000 ug/m3) to NULL, and removes empty and duplicate rows. It also adds a
  simple `above_who_pm25` flag.
- **Load:** upserts into Azure SQL Database with a T-SQL `MERGE`, using `(city, time)` as the
  primary key, so re-running the pipeline never creates duplicates (idempotent). The same
  pipeline loads into a local SQLite file when no Azure settings are present.
- **Resilience:** the free serverless Azure database pauses when idle, so the connection step
  retries while it wakes up. One failing city does not stop the others.
- **Monitoring:** every run is logged per city in a `pipeline_runs` table.
- **Testing:** 7 pytest tests cover cleaning, idempotent loading, failure handling and the
  Azure upsert logic.
- **Automation:** a GitHub Actions workflow runs the tests and the pipeline daily at 06:00 UTC.
  Database credentials are stored as GitHub Actions secrets, never in the code.

## Project structure

```
etl/            config.py, extract.py, transform.py, load.py (SQLite), load_azure.py (Azure SQL)
tests/          test_pipeline.py, test_azure_load.py
sql/            analysis.sql (aggregation, window function, CTE and join examples, SQLite syntax)
data/           air_quality.db (local SQLite snapshot from the initial backfill)
run_pipeline.py entry point
.github/workflows/daily.yml
```

## Run it yourself

**Locally (SQLite):**

```bash
pip install -r requirements.txt
pytest -q
python run_pipeline.py --past-days 90   # one-off backfill of recent history
python run_pipeline.py                  # normal run (last 2 days)
```

**Against your own Azure SQL Database:** set these environment variables before running
`python run_pipeline.py`. The tables are created automatically on the first run.

```
AZURE_SQL_SERVER     e.g. your-server.database.windows.net
AZURE_SQL_DATABASE   e.g. airquality
AZURE_SQL_USER
AZURE_SQL_PASSWORD
```

In GitHub, add the same four names as repository secrets. The workflow can also be started
manually from the Actions tab, with a `past_days` input for a backfill.

Example queries are in `sql/analysis.sql`. They use SQLite syntax (for example `strftime`),
so some functions need translating for T-SQL.

## Data source and limitations

Data comes from the [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api).
Values are modelled estimates from the Copernicus Atmosphere Monitoring Service (CAMS) European
air-quality model at roughly 11 km resolution, not readings from ground sensors. Each city is
therefore represented by one model grid cell, so results describe regional air quality rather
than street-level conditions.

`above_who_pm25` marks hours where PM2.5 exceeds the WHO 2021 24-hour guideline of 15 ug/m3.
The guideline is defined for 24-hour averages, so applying it to hourly values is a simple
indicator, not an official compliance measure.

**Known limitation:** the Azure load runs one `MERGE` per row, so a 90-day backfill takes
around 20 minutes. The daily run (about 72 hours per city) is much faster.

Attribution: contains data from CAMS ENSEMBLE (Copernicus Atmosphere Monitoring Service),
accessed via Open-Meteo.

## Next steps

- Batch the `MERGE` statements to make large backfills much faster.
- Analyse the daily NO2 pattern by hour (rush-hour peaks) and compare weekdays with weekends.
- Add a Tableau or Power BI dashboard connected to the Azure database.

## Author

Muhammad Usman Khan, Bristol, UK