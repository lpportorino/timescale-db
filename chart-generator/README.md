# Chart Generator Task

## Your Mission

Create a command-line tool that generates HTML charts from TimescaleDB data. This tool should connect to the database, query time-series data, and produce beautiful charts that can be viewed in a web browser.

## Task Requirements

### 1. Command-Line Interface

Your tool must accept these arguments:
- `--metric` - Type of data to chart (required)
  - `temperature` - Weather station temperature readings
  - `health` - Service health percentages
  - `power` - Power consumption by service
- `--window` - Time period to display (required)
  - `1h` - Last hour
  - `24h` - Last 24 hours
  - `7d` - Last 7 days
- `--output` - Output filename (optional, default: `chart.html`)

Example usage:
```bash
./chart-generator --metric temperature --window 24h
./chart-generator --metric health --window 1h --output health-report.html
```

### 2. Database Connection

- Host: `sych.local` (make sure this is in your `/etc/hosts` file!)
- Port: 8094
- Username: jettison
- Password: aMvzpGPgNVtH53S
- Database: jettison

### 3. Data Sources

You'll be querying these tables:

#### Temperature Data (`meteo_metrics`)
```sql
-- Columns: time, station, temperature, humidity, pressure
SELECT time, station, temperature 
FROM meteo_metrics 
WHERE time >= NOW() - INTERVAL '24 hours'
ORDER BY time, station;
```

#### Health Metrics (`health_metrics_1min_cagg`)
```sql
-- Columns: time, service, category, avg_health, min_percentage, max_percentage
SELECT time, service, category, avg_health
FROM health_metrics_1min_cagg
WHERE time >= NOW() - INTERVAL '1 hour'
ORDER BY time, service;
```

#### Power Consumption (`power_metrics`)
```sql
-- Columns: time, service_name, channel, voltage, current, power
SELECT time, service_name, power
FROM power_metrics
WHERE time >= NOW() - INTERVAL '7 days'
ORDER BY time, service_name;
```

### 4. Output Requirements

Generate a single HTML file that contains:
1. A chart visualization (line chart for temperature/health, bar chart for power)
2. A title showing the metric type and time window
3. A timestamp showing when the chart was generated
4. The chart should be interactive (tooltips, zoom, etc.)

### 5. Docker Requirements

Your solution must:
- Include a `Dockerfile` that builds your application
- Include a `Makefile` with these targets:
  - `make build` - Build the Docker image
  - `make run ARGS="..."` - Run the chart generator
  - `make clean` - Remove generated files
  - `make help` - Show usage information
- Run on the host network (use `--network host`)
- Output files should appear in the current directory


Good luck! We're excited to see your solution!
