# CLAUDE.md - Chart Generator Implementation Hints

## Overview

This file provides implementation hints and technical guidance for the chart generator task. Use these hints to help you build a successful solution.

## Go Package Recommendations

### Database Connection
```go
import (
    "database/sql"
    _ "github.com/lib/pq"  // PostgreSQL driver
)
```

### Command-Line Arguments
```go
import "flag"  // Built-in flag package for parsing arguments
```

### HTML Generation
```go
import "html/template"  // For generating HTML with data
```

## Implementation Hints

### 1. Database Connection String

```go
connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
    host, port, user, password, dbname)
db, err := sql.Open("postgres", connStr)
```

### 2. Time Window Conversion

Map user-friendly inputs to PostgreSQL intervals:
```go
windowMap := map[string]string{
    "1h":  "1 hour",
    "24h": "24 hours",
    "7d":  "7 days",
}
```

### 3. Query Optimization

For large time windows, consider aggregating data:
```sql
-- Instead of every row, bucket by time
SELECT time_bucket('5 minutes', time) AS bucket,
       station,
       AVG(temperature) as avg_temp
FROM meteo_metrics
WHERE time >= NOW() - INTERVAL '24 hours'
GROUP BY bucket, station
ORDER BY bucket;
```

### 4. HTML Template Structure

Consider this approach for generating HTML:
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{.Title}}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <canvas id="myChart"></canvas>
    <script>
        const data = {
            labels: {{.Labels}},
            datasets: {{.Datasets}}
        };
        new Chart(document.getElementById('myChart'), {
            type: '{{.ChartType}}',
            data: data
        });
    </script>
</body>
</html>
```

### 5. Docker Multi-Stage Build

Use a multi-stage build for smaller images:
```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o chart-generator

# Runtime stage
FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/chart-generator /
CMD ["/chart-generator"]
```

### 6. Makefile Pattern

Follow the pattern from other directories:
```makefile
.PHONY: help build run clean

help:
	@echo "Available commands..."

build:
	docker build -t chart-generator .

run: build
	docker run --rm --network host -v $$(pwd):/output chart-generator $(ARGS)
```

## Common Pitfalls to Avoid

### 1. Time Zone Issues
- Database stores timestamps in UTC
- Consider how to display times to users
- The sample data is from July 2025

### 2. Empty Result Sets
- Handle cases where queries return no data
- Provide helpful error messages

### 3. SQL Injection
- Use parameterized queries, not string concatenation
- Even though this is internal, practice good security

### 4. Memory Usage
- Don't load millions of rows into memory
- Use time bucketing for large time windows
- Stream results if needed

### 5. File Permissions
- Docker runs as root by default
- Output files may have root ownership
- Consider using `-u` flag or chown in Dockerfile

## Data Patterns

### Temperature Data
- 20 weather stations (station-0 through station-19)
- Readings every few minutes
- Temperature in Celsius, humidity in %, pressure in hPa

### Health Metrics
- Multiple services with categories
- Values are percentages (0-100)
- Pre-aggregated to 1-minute intervals

### Power Metrics
- Service-based consumption
- Power in watts, voltage in volts, current in amps
- High-frequency data (every few seconds)

## Testing Your Solution

1. **Basic Functionality:**
   ```bash
   make run ARGS="--metric temperature --window 1h"
   # Should generate chart.html
   ```

2. **Error Cases:**
   ```bash
   # Missing arguments
   make run
   
   # Invalid metric
   make run ARGS="--metric invalid --window 1h"
   
   # Database not running
   cd ../db && make stop
   cd ../chart-generator && make run ARGS="--metric temperature --window 1h"
   ```

3. **Edge Cases:**
   - No data in time window
   - Very large time window (7d)
   - Special characters in output filename

## Performance Considerations

### Query Performance
- Use indexes (TimescaleDB creates them automatically)
- Limit data points for readability (aggregate if > 1000 points)
- Consider continuous aggregates for faster queries

### Chart Rendering
- Too many data points slow down browsers
- Group by larger time buckets for long periods
- Limit number of series (e.g., top 10 stations)

## Alternative Approaches

### SVG Generation
If you prefer server-side rendering:
- `github.com/wcharczuk/go-chart` - Simple charting
- `gonum.org/v1/plot` - Scientific plotting

### Excel Generation
For downloadable reports:
- `github.com/xuri/excelize/v2` - Excel file generation
- Can embed charts directly in Excel

### JSON API
Instead of HTML, you could:
- Generate JSON data
- Serve a static HTML file that fetches JSON
- More flexible but more complex

## Remember

1. **Start simple** - Get a basic version working first
2. **Iterate** - Add features incrementally
3. **Test often** - Run your code frequently
4. **Ask questions** - If requirements are unclear
5. **Document** - Help the next developer understand your code

Good luck with your implementation!