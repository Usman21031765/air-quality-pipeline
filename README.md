# UK Air Quality Data Pipeline

An automated ETL pipeline that collects hourly air-quality data for five UK cities, cleans and
validates it, and stores it in a SQL database ready for analysis. A scheduled GitHub Actions
workflow runs it every day, so the dataset keeps growing without manual work.

**Business question:** How does air quality in Bristol compare with other major UK cities?

**Tech stack:** Python (pandas, requests), SQL (SQLite), pytest, GitHub Actions

## Key findings

Based on a 90-day backfill (about 2,184 hourly readings per city, up to early October 2026):

| City | Average PM2.5 (ug/m3) | Hours above WHO guideline |
|---|---|---|
| London | 6.4 | 2.3% |
| Manchester | 5.9 | 1.4% |
| **Bristol** | **5.6** | **1.1%** |
| Birmingham | 5.5 | 0.4% |
| Leeds | 5.4 | 0.3% |

- London had the highest average PM2.5 and the largest share of hours above the WHO guideline.
  Bristol ranked third of five.
- All five cities averaged well below the WHO 24-hour guideline of 15 ug/m3.
- The differences between cities are small (5.4 to 6.4 ug/m3), and the window covers only about
  three months of summer and autumn, so these results should not be read as a full-year picture.
  The table is a snapshot, and the numbers will shift as the daily pipeline adds more data.

## How it works

```
Open-Meteo Air Quality API --> extract.py --> transform.py --> load.py --> SQLite database
      (hourly JSON)            fetch + retry   clean + validate  upsert      air_quality
                                                                             pipeline_runs
                                      ^
                       GitHub Actions: run tests, then the pipeline, every day
```

- **Extract:** requests hourly PM10, PM2.5, nitrogen dioxide and ozone for each city, with
  timeouts and automatic retries.
- **Transform:** standardises timestamps to UTC, forces numeric types, sets impossible values
  (negative or above 1000 ug/m3) to NULL, and removes empty and duplicate rows. It also adds a
  simple `above_who_pm25` flag.
- **Load:** upserts into SQLite using `(city, time)` as the primary key, so re-running the
  pipeline never creates duplicates (idempotent).
- **Monitoring:** every run is logged per city in a `pipeline_runs` table, and one failing city
  does not stop the others.
- **Testing:** 5 pytest tests cover cleaning, idempotent loading and failure handling.
- **Automation:** a GitHub Actions workflow runs the tests and the pipeline daily at 06:00 UTC and
  commits the updated database.

## Project structure

```
etl/            config.py, extract.py, transform.py, load.py
tests/          test_pipeline.py
sql/            analysis.sql (aggregation, window function, CTE and join examples)
data/           air_quality.db (SQLite database, updated daily)
run_pipeline.py entry point
.github/workflows/daily.yml
```

## Run it yourself

```bash
pip install -r requirements.txt
pytest -q
python run_pipeline.py --past-days 90   # one-off backfill of recent history
python run_pipeline.py                  # normal run (last 2 days)
```

Example queries are in `sql/analysis.sql`.

## Data source and limitations

Data comes from the [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api).
Values are modelled estimates from the Copernicus Atmosphere Monitoring Service (CAMS) European
air-quality model at roughly 11 km resolution, not readings from ground sensors. Each city is
therefore represented by one model grid cell, so results describe regional air quality rather
than street-level conditions.

`above_who_pm25` marks hours where PM2.5 exceeds the WHO 2021 24-hour guideline of 15 ug/m3.
The guideline is defined for 24-hour averages, so applying it to hourly values is a simple
indicator, not an official compliance measure.

Attribution: contains data from CAMS ENSEMBLE (Copernicus Atmosphere Monitoring Service),
accessed via Open-Meteo.

## Next steps

- Deploy the pipeline to the cloud (AWS or Azure free tier) with a managed database.
- Analyse the daily NO2 pattern by hour (rush-hour peaks) and compare weekdays with weekends.
- Add a Tableau or Power BI dashboard on top of the database.

## Author

Muhammad Usman Khan, Bristol, UK