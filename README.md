# UK Air Quality Data Pipeline

An automated ETL pipeline that pulls hourly air-quality data for five UK cities every day,
cleans and validates it, and stores it in a SQL database ready for analysis and dashboards.

**Business question:** How does air quality in Bristol compare with other major UK cities,
and at what times of day is it worst?

## Architecture

```
Open-Meteo Air Quality API  ->  extract.py  ->  transform.py  ->  load.py  ->  SQLite (air_quality)
        (JSON, hourly)          retries         clean/validate    upsert        + pipeline_runs log
                                                                        ^
                                                        GitHub Actions: tests + run daily
```

## Run it

```bash
pip install -r requirements.txt
pytest -q                 # unit tests
python run_pipeline.py --past-days 90   # one-off backfill of recent history
python run_pipeline.py                  # normal daily run (last 2 days)
```

Then open `sql/analysis.sql` for example queries (window functions, CTEs, joins).

## Design decisions

- **Idempotent loads:** rows are upserted on `(city, time)`, so re-running never creates duplicates.
- **Data quality checks:** invalid timestamps removed, values forced numeric, out-of-range values
  set to NULL, empty and duplicate rows dropped.
- **Fault tolerance:** API calls retry with backoff; one failing city does not stop the others.
- **Observability:** every run is logged per city in the `pipeline_runs` table.
- **Tested:** unit tests cover cleaning, idempotent loading and failure handling.
- **Automated:** a scheduled GitHub Actions workflow runs the tests, then the pipeline, daily.

## Data source

Hourly air-quality data comes from the [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api).
The values are modelled estimates from the Copernicus Atmosphere Monitoring Service (CAMS)
European air-quality model at roughly 11 km resolution, not readings from ground sensors.
Each city is therefore represented by one model grid cell, so results show regional
air quality rather than street-level conditions.

Attribution: contains data from CAMS ENSEMBLE (Copernicus Atmosphere Monitoring Service),
accessed via Open-Meteo.

Pollutants: PM10, PM2.5, nitrogen dioxide, ozone. `above_who_pm25` is a simple indicator
(hourly PM2.5 above the WHO 24-hour guideline of 15 ug/m3), not an official compliance measure.

## Key findings

_Add 3 findings from your own analysis here once you have a few weeks of data._

## Phase 2: cloud deployment

_Describe where you deployed it (e.g. AWS Lambda + RDS/S3, or Azure Functions + Azure SQL)
and add a short architecture note and screenshot._
