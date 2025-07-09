# ⏰ TimescaleDB - Time-Series Databases Explained!

> **What's a time-series database?** It's a database optimized for data that changes over time - like temperature readings, stock prices, or server metrics!

## 📚 Table of Contents

1. [What is Time-Series Data?](#-what-is-time-series-data)
2. [Why TimescaleDB?](#-why-timescaledb)
3. [Key Concepts](#-key-concepts)
4. [SQL Queries for Time-Series](#-sql-queries-for-time-series)
5. [Our Project's Data Model](#-our-projects-data-model)
6. [Hands-On Examples](#-hands-on-examples)
7. [Advanced Features](#-advanced-features)

## 📊 What is Time-Series Data?

Time-series data is any data that has a timestamp. Think of it as a diary of measurements!

### Real-World Examples

1. **🌡️ Weather Station**
   ```
   Time                  | Temperature | Humidity | Pressure
   2024-01-15 09:00:00  | 72.5°F      | 45%      | 30.12
   2024-01-15 09:05:00  | 72.8°F      | 44%      | 30.13
   2024-01-15 09:10:00  | 73.1°F      | 43%      | 30.13
   ```

2. **💻 Server Monitoring**
   ```
   Time                  | CPU Usage | Memory | Disk I/O
   2024-01-15 09:00:00  | 45%       | 8.2GB  | 120MB/s
   2024-01-15 09:00:10  | 52%       | 8.5GB  | 95MB/s
   2024-01-15 09:00:20  | 48%       | 8.3GB  | 110MB/s
   ```

3. **📈 Stock Prices**
   ```
   Time                  | Symbol | Price   | Volume
   2024-01-15 09:30:00  | AAPL   | $185.92 | 1,234,567
   2024-01-15 09:30:01  | AAPL   | $185.93 | 987,654
   2024-01-15 09:30:02  | AAPL   | $185.91 | 1,456,789
   ```

### Characteristics of Time-Series Data

1. **📈 Append-Only** - New data is added, old data rarely changes
2. **🕐 Time-Ordered** - Data naturally ordered by time
3. **📊 High Volume** - Often collecting data every second or faster
4. **🔍 Time-Based Queries** - "Show me last hour" or "Average per day"

## 🚀 Why TimescaleDB?

### Regular PostgreSQL vs TimescaleDB

Imagine you have a bookshelf:
- **PostgreSQL** = Regular bookshelf (works fine for a few books)
- **TimescaleDB** = Library with a cataloging system (handles millions of books efficiently)

### TimescaleDB Benefits

1. **⚡ 100x Faster Queries** - Optimized for time-based queries
2. **📦 Automatic Partitioning** - Data organized by time chunks
3. **🗜️ Compression** - Reduces storage by 90%+
4. **📊 Continuous Aggregates** - Pre-calculated summaries
5. **🐘 Still PostgreSQL** - All PostgreSQL features still work!

## 🎯 Key Concepts

### 1. Hypertables

A hypertable looks like a regular table but is actually many smaller tables (chunks) behind the scenes.

```sql
-- Create a regular table
CREATE TABLE temperature (
    time        TIMESTAMPTZ NOT NULL,
    location    TEXT NOT NULL,
    temperature DOUBLE PRECISION
);

-- Convert it to a hypertable (TimescaleDB magic!)
SELECT create_hypertable('temperature', 'time');
```

**Visual Representation:**
```
Regular Table:              Hypertable:
┌─────────────┐            ┌─────────────┐
│             │            │   Virtual   │
│  All Data   │     →      │    View     │
│  In One     │            └──────┬──────┘
│   Place     │                   │
└─────────────┘            ┌──────┴──────┐
                          │              │
                    ┌─────▼───┐  ┌──────▼────┐
                    │ Chunk 1 │  │  Chunk 2  │
                    │ Jan 1-7 │  │ Jan 8-14  │
                    └─────────┘  └───────────┘
```

### 2. Time Bucketing

Time bucketing groups data into time intervals - like summarizing by hour, day, or week.

```sql
-- Raw data (every minute)
SELECT time, temperature FROM sensor_data;

-- Bucketed by hour (average per hour)
SELECT 
    time_bucket('1 hour', time) AS hour,
    AVG(temperature) as avg_temp
FROM sensor_data
GROUP BY hour
ORDER BY hour;
```

**Example Output:**
```
Without Bucketing:          With 1-hour Buckets:
09:00 - 72.5°F             09:00 - 72.8°F (avg)
09:15 - 72.8°F             10:00 - 73.5°F (avg)
09:30 - 73.1°F             11:00 - 74.2°F (avg)
09:45 - 73.2°F
10:00 - 73.5°F
... (many rows)            ... (fewer rows)
```

### 3. Continuous Aggregates

These are like "saved searches" that automatically update. Perfect for dashboards!

```sql
-- Create a continuous aggregate for hourly averages
CREATE MATERIALIZED VIEW hourly_temperature
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', time) AS hour,
    location,
    AVG(temperature) as avg_temp,
    MAX(temperature) as max_temp,
    MIN(temperature) as min_temp
FROM temperature
GROUP BY hour, location;

-- Query it like a regular table (SUPER FAST!)
SELECT * FROM hourly_temperature
WHERE hour >= NOW() - INTERVAL '24 hours';
```

### 4. Compression

TimescaleDB can compress old data automatically, saving 90%+ disk space!

```sql
-- Enable compression on a hypertable
ALTER TABLE temperature SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'location'
);

-- Compress chunks older than 7 days
SELECT add_compression_policy('temperature', INTERVAL '7 days');
```

## 🔍 SQL Queries for Time-Series

### Basic Time-Series Queries

```sql
-- 1. Last N hours of data
SELECT * FROM temperature
WHERE time >= NOW() - INTERVAL '3 hours'
ORDER BY time DESC;

-- 2. Data for a specific day
SELECT * FROM temperature
WHERE time::date = '2024-01-15'
ORDER BY time;

-- 3. Average per hour for last 24 hours
SELECT 
    time_bucket('1 hour', time) as hour,
    AVG(temperature) as avg_temp
FROM temperature
WHERE time >= NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;

-- 4. Find temperature spikes
SELECT * FROM temperature
WHERE temperature > 100
AND time >= NOW() - INTERVAL '7 days';

-- 5. Compare today vs yesterday
WITH today AS (
    SELECT AVG(temperature) as avg_temp
    FROM temperature
    WHERE time >= CURRENT_DATE
    AND time < CURRENT_DATE + INTERVAL '1 day'
),
yesterday AS (
    SELECT AVG(temperature) as avg_temp
    FROM temperature
    WHERE time >= CURRENT_DATE - INTERVAL '1 day'
    AND time < CURRENT_DATE
)
SELECT 
    today.avg_temp as today_avg,
    yesterday.avg_temp as yesterday_avg,
    today.avg_temp - yesterday.avg_temp as difference
FROM today, yesterday;
```

### Advanced Queries

```sql
-- Moving average (smooth out noise)
SELECT 
    time,
    temperature,
    AVG(temperature) OVER (
        ORDER BY time
        ROWS BETWEEN 5 PRECEDING AND 5 FOLLOWING
    ) as moving_avg
FROM temperature
WHERE location = 'sensor_1';

-- Rate of change
SELECT 
    time,
    temperature,
    temperature - LAG(temperature) OVER (ORDER BY time) as change
FROM temperature
WHERE location = 'sensor_1';

-- Find missing data (gap detection)
SELECT 
    time,
    LEAD(time) OVER (ORDER BY time) - time as gap
FROM temperature
WHERE LEAD(time) OVER (ORDER BY time) - time > INTERVAL '5 minutes';
```

## 📁 Our Project's Data Model

Let's understand the tables in our sample database:

### 1. Weather Metrics (`meteo_metrics`)

```sql
CREATE TABLE meteo_metrics (
    time        TIMESTAMPTZ NOT NULL,
    station     TEXT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity    DOUBLE PRECISION,
    pressure    DOUBLE PRECISION
);
```

**Sample Data:**
```
2025-07-04 09:00:00 | Weather_Station_1 | 72.5 | 45.2 | 30.12
2025-07-04 09:00:00 | Weather_Station_2 | 71.8 | 46.8 | 30.10
```

### 2. Health Metrics (`health_metrics_raw`)

```sql
CREATE TABLE health_metrics_raw (
    time  TIMESTAMPTZ NOT NULL,
    state JSONB NOT NULL  -- Flexible JSON data
);
```

**Sample JSON Data:**
```json
{
    "service": "web_server",
    "health": 98.5,
    "response_time_ms": 45,
    "active_connections": 1234
}
```

### 3. Continuous Aggregate (`health_metrics_1min_cagg`)

This pre-calculates 1-minute summaries:

```sql
CREATE MATERIALIZED VIEW health_metrics_1min_cagg AS
SELECT 
    time_bucket('1 minute', time) as time,
    service,
    category,
    AVG(health) as avg_health,
    MIN(percentage) as min_percentage,
    MAX(percentage) as max_percentage
FROM health_metrics_processed
GROUP BY time_bucket('1 minute', time), service, category;
```

## 🎯 Hands-On Examples

### Example 1: Temperature Analysis

```sql
-- Find hottest hour of each day
SELECT 
    time::date as day,
    EXTRACT(hour FROM time) as hour,
    MAX(temperature) as max_temp
FROM meteo_metrics
GROUP BY day, hour
ORDER BY max_temp DESC
LIMIT 10;

-- Temperature trends by station
SELECT 
    station,
    time_bucket('1 day', time) as day,
    AVG(temperature) as avg_temp,
    MIN(temperature) as min_temp,
    MAX(temperature) as max_temp
FROM meteo_metrics
WHERE time >= '2025-07-01' AND time < '2025-07-05'
GROUP BY station, day
ORDER BY station, day;
```

### Example 2: System Health Monitoring

```sql
-- Services with health below 95% in last hour
SELECT DISTINCT service, MIN(avg_health) as worst_health
FROM health_metrics_1min_cagg
WHERE time >= NOW() - INTERVAL '1 hour'
GROUP BY service
HAVING MIN(avg_health) < 95
ORDER BY worst_health;

-- Health trend over time
SELECT 
    time_bucket('15 minutes', time) as period,
    service,
    AVG(avg_health) as health
FROM health_metrics_1min_cagg
WHERE service = 'web_server'
AND time >= NOW() - INTERVAL '6 hours'
GROUP BY period, service
ORDER BY period;
```

### Example 3: Power Consumption

```sql
-- Total power consumption by hour
SELECT 
    time_bucket('1 hour', time) as hour,
    SUM(power) as total_power_kwh
FROM power_metrics
WHERE time >= '2025-07-04'
GROUP BY hour
ORDER BY hour;

-- Find power spikes
WITH power_stats AS (
    SELECT 
        AVG(power) as avg_power,
        STDDEV(power) as std_power
    FROM power_metrics
    WHERE time >= NOW() - INTERVAL '24 hours'
)
SELECT 
    p.time,
    p.module,
    p.power
FROM power_metrics p, power_stats s
WHERE p.power > s.avg_power + (2 * s.std_power)  -- 2 standard deviations
ORDER BY p.time DESC;
```

## 🚀 Advanced Features

### 1. Data Retention Policies

Automatically delete old data:

```sql
-- Keep only last 30 days of raw data
SELECT add_retention_policy('temperature', INTERVAL '30 days');

-- Keep aggregates longer
SELECT add_retention_policy('hourly_temperature', INTERVAL '1 year');
```

### 2. Real-Time Aggregation

```sql
-- Refresh continuous aggregate every 10 minutes
SELECT add_continuous_aggregate_policy('hourly_temperature',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes');
```

### 3. Data Tiering

Move old data to cheaper storage:

```sql
-- Move chunks older than 3 months to slow storage
SELECT move_chunk(
    chunk => c.chunk_name,
    destination_tablespace => 'slow_ssd'
)
FROM show_chunks('temperature', older_than => INTERVAL '3 months') c;
```

## 📚 Learning Resources

### Official Resources
- 📖 **[TimescaleDB Docs](https://docs.timescale.com/)** - Comprehensive documentation
- 🎓 **[TimescaleDB Tutorial](https://docs.timescale.com/getting-started/latest/)** - Step-by-step guide
- 📺 **[TimescaleDB YouTube](https://www.youtube.com/c/TimescaleDB)** - Video tutorials

### Interactive Learning
- 🎮 **[TimescaleDB Playground](https://www.timescale.com/playground)** - Try queries online
- 📊 **[Sample Datasets](https://docs.timescale.com/use-timescale/latest/tutorials/sample-datasets/)** - Practice data

### Courses & Tutorials
- 🎓 **[Time-Series Forecasting](https://docs.timescale.com/use-timescale/latest/tutorials/time-series-forecast/)** - Advanced tutorial
- 📖 **[IoT Tutorial](https://docs.timescale.com/use-timescale/latest/tutorials/simulate-iot-sensor-data/)** - Build an IoT system

## 💡 Best Practices

1. **Always use time column in WHERE clause** - Helps query performance
2. **Create indexes on frequently filtered columns** - Like location, sensor_id
3. **Use continuous aggregates for dashboards** - Much faster than raw queries
4. **Compress old data** - Save 90%+ storage
5. **Set retention policies** - Don't keep data forever

## 🎯 Quick SQL Reference for Time-Series

```sql
-- Time intervals
NOW()                           -- Current time
NOW() - INTERVAL '1 hour'      -- 1 hour ago
NOW() - INTERVAL '7 days'      -- 7 days ago
CURRENT_DATE                    -- Today at 00:00:00
CURRENT_DATE - INTERVAL '1 day' -- Yesterday

-- Time bucketing
time_bucket('5 minutes', time)  -- 5-minute buckets
time_bucket('1 hour', time)     -- Hourly buckets
time_bucket('1 day', time)      -- Daily buckets

-- Date/time extraction
EXTRACT(hour FROM time)         -- Hour (0-23)
EXTRACT(dow FROM time)          -- Day of week (0-6)
time::date                      -- Just the date part
time::time                      -- Just the time part

-- Window functions
LAG(value) OVER (ORDER BY time)     -- Previous value
LEAD(value) OVER (ORDER BY time)    -- Next value
AVG(value) OVER (ORDER BY time      -- Moving average
    ROWS BETWEEN 5 PRECEDING 
    AND 5 FOLLOWING)
```

## 🏁 What's Next?

Now that you understand TimescaleDB:
1. Explore our database with `make explore`
2. Try writing custom queries in the example app
3. Learn about continuous aggregates in depth
4. Build your own time-series application!

---

**Remember**: Time-series databases are just databases optimized for time-stamped data. Start with simple queries and gradually explore advanced features! 🚀

*Next: Check out [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions!*