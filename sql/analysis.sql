-- Run against data/air_quality.db once you have a few days of data.

-- 1. Average PM2.5 and share of hours above the WHO guideline, by city
SELECT city,
       ROUND(AVG(pm2_5), 1)                    AS avg_pm25,
       ROUND(100.0 * AVG(above_who_pm25), 1)   AS pct_hours_above_who
FROM air_quality
GROUP BY city
ORDER BY avg_pm25 DESC;

-- 2. Which hour of the day is worst for NO2? (rush-hour pattern)
SELECT CAST(strftime('%H', time) AS INTEGER) AS hour_utc,
       ROUND(AVG(nitrogen_dioxide), 1)       AS avg_no2
FROM air_quality
WHERE city = 'Bristol'
GROUP BY hour_utc
ORDER BY avg_no2 DESC;

-- 3. Rank cities within each day by average PM2.5 (window function)
WITH daily AS (
    SELECT city, DATE(time) AS day, AVG(pm2_5) AS avg_pm25
    FROM air_quality
    GROUP BY city, day
)
SELECT day, city, ROUND(avg_pm25, 1) AS avg_pm25,
       RANK() OVER (PARTITION BY day ORDER BY avg_pm25 DESC) AS rank_in_day
FROM daily
ORDER BY day, rank_in_day;

-- 4. Bristol vs the average of the other cities, per day (CTE + join)
WITH daily AS (
    SELECT city, DATE(time) AS day, AVG(pm2_5) AS avg_pm25
    FROM air_quality GROUP BY city, day
)
SELECT b.day,
       ROUND(b.avg_pm25, 1)  AS bristol,
       ROUND(AVG(o.avg_pm25), 1) AS other_cities_avg
FROM daily b
JOIN daily o ON o.day = b.day AND o.city <> 'Bristol'
WHERE b.city = 'Bristol'
GROUP BY b.day, b.avg_pm25
ORDER BY b.day;
