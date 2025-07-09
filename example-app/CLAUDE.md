# CLAUDE.md - Example Application

## Overview

Template application demonstrating TimescaleDB connectivity and query patterns using Go. Designed as a starting point for building time-series data applications.

## Architecture

### Current Structure

```
main.go
├── Database connection setup
├── Query functions for each metric type
└── Main execution with examples
```

### Extension Pattern

For chart generation tasks:
```
your_app.go
├── Argument parsing (metric, window, output)
├── Database queries with time windows
├── Data processing/aggregation
├── Chart generation (go-chart/gonum)
└── Output handling (SVG/Excel)
```

## Implementation Patterns

### Connection Management

```go
// Environment-based configuration
config := DBConfig{
    Host:     getEnv("PGHOST", "sych.local"),
    Port:     getEnv("PGPORT", "8094"),
    User:     getEnv("PGUSER", "jettison"),
    Password: getEnv("PGPASSWORD", "aMvzpGPgNVtH53S"),
    Database: getEnv("PGDATABASE", "jettison"),
}

// Connection with error handling
connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
    config.Host, config.Port, config.User, config.Password, config.Database)

db, err := sql.Open("postgres", connStr)
if err != nil {
    return nil, err
}
```

### Time Window Queries

```go
func queryWithWindow(db *sql.DB, window string) error {
    // Parse window: "1h", "24h", "7d"
    var interval string
    switch {
    case strings.HasSuffix(window, "h"):
        hours := strings.TrimSuffix(window, "h")
        interval = fmt.Sprintf("%s hours", hours)
    case strings.HasSuffix(window, "d"):
        days := strings.TrimSuffix(window, "d")
        interval = fmt.Sprintf("%s days", days)
    }
    
    query := fmt.Sprintf(`
        SELECT * FROM metrics
        WHERE time >= NOW() - INTERVAL '%s'
    `, interval)
    
    // Execute query...
}
```

### Metric Type Handling

```go
type MetricConfig struct {
    Table       string
    ValueColumn string
    GroupBy     string
}

var metricTypes = map[string]MetricConfig{
    "temperature": {
        Table:       "meteo_metrics",
        ValueColumn: "temperature",
        GroupBy:     "station",
    },
    "health": {
        Table:       "health_metrics_1min_cagg",
        ValueColumn: "avg_health",
        GroupBy:     "service",
    },
    "power": {
        Table:       "power_metrics",
        ValueColumn: "power",
        GroupBy:     "service_name",
    },
}
```

## Chart Generation Examples

### SVG with go-chart

```go
import (
    "github.com/wcharczuk/go-chart/v2"
    "github.com/wcharczuk/go-chart/v2/drawing"
)

func generateSVGChart(data []DataPoint, outputPath string) error {
    xValues := make([]time.Time, len(data))
    yValues := make([]float64, len(data))
    
    for i, point := range data {
        xValues[i] = point.Time
        yValues[i] = point.Value
    }
    
    graph := chart.Chart{
        XAxis: chart.XAxis{
            Name: "Time",
            Style: chart.Style{
                TextRotationDegrees: 45.0,
            },
        },
        YAxis: chart.YAxis{
            Name: "Value",
        },
        Series: []chart.Series{
            chart.TimeSeries{
                XValues: xValues,
                YValues: yValues,
            },
        },
    }
    
    f, err := os.Create(outputPath)
    if err != nil {
        return err
    }
    defer f.Close()
    
    return graph.Render(chart.SVG, f)
}
```

### Excel with excelize

```go
import "github.com/xuri/excelize/v2"

func generateExcelChart(data []DataPoint, outputPath string) error {
    f := excelize.NewFile()
    
    // Write data
    for i, point := range data {
        row := i + 2
        f.SetCellValue("Sheet1", fmt.Sprintf("A%d", row), point.Time)
        f.SetCellValue("Sheet1", fmt.Sprintf("B%d", row), point.Value)
    }
    
    // Create chart
    if err := f.AddChart("Sheet1", "D1", &excelize.Chart{
        Type: excelize.Line,
        Series: []excelize.ChartSeries{
            {
                Categories: fmt.Sprintf("Sheet1!$A$2:$A$%d", len(data)+1),
                Values:     fmt.Sprintf("Sheet1!$B$2:$B$%d", len(data)+1),
                Name:       "Metric Over Time",
            },
        },
        Title: excelize.ChartTitle{
            Name: "TimescaleDB Metrics",
        },
    }); err != nil {
        return err
    }
    
    return f.SaveAs(outputPath)
}
```

## Common Patterns

### Aggregation Windows

For performance with large datasets:
```go
func getTableForWindow(windowHours int) string {
    switch {
    case windowHours >= 24:
        return "metrics_hourly_cagg"  // Use hourly aggregates
    case windowHours >= 1:
        return "metrics_5min_cagg"     // Use 5-minute aggregates
    default:
        return "metrics"               // Raw data
    }
}
```

### Multiple Series

```go
// Query with grouping
query := `
    SELECT 
        time_bucket('5 minutes', time) as bucket,
        station,
        AVG(temperature) as avg_temp
    FROM meteo_metrics
    WHERE time >= $1
    GROUP BY bucket, station
    ORDER BY bucket, station
`

// Organize by series
seriesData := make(map[string][]DataPoint)
for rows.Next() {
    var bucket time.Time
    var station string
    var avgTemp float64
    
    rows.Scan(&bucket, &station, &avgTemp)
    seriesData[station] = append(seriesData[station], DataPoint{
        Time:  bucket,
        Value: avgTemp,
    })
}
```

## Docker Considerations

### Multi-stage Build

```dockerfile
# Build stage
FROM golang:1.22-alpine AS builder
WORKDIR /build
COPY go.mod go.sum* ./
RUN go mod download
COPY *.go ./
RUN go build -o app .

# Runtime stage
FROM alpine:3.19
RUN apk add --no-cache ca-certificates
WORKDIR /app
COPY --from=builder /build/app .
CMD ["./app"]
```

### Adding Dependencies

```dockerfile
# For chart generation
RUN go get github.com/wcharczuk/go-chart/v2
RUN go get github.com/xuri/excelize/v2
RUN go get gonum.org/v1/plot
```

## Performance Tips

1. **Use Prepared Statements** - Avoid query parsing overhead
2. **Connection Pooling** - Set appropriate pool size
3. **Time Bucketing** - Reduce data points for visualization
4. **Concurrent Queries** - Use goroutines for parallel fetches
5. **Result Streaming** - Process large results incrementally

## Error Handling

### Robust Query Execution

```go
func safeQuery(db *sql.DB, query string, args ...interface{}) ([][]interface{}, error) {
    rows, err := db.Query(query, args...)
    if err != nil {
        return nil, fmt.Errorf("query failed: %w", err)
    }
    defer rows.Close()
    
    // Get column info
    cols, err := rows.Columns()
    if err != nil {
        return nil, err
    }
    
    var results [][]interface{}
    for rows.Next() {
        values := make([]interface{}, len(cols))
        valuePtrs := make([]interface{}, len(cols))
        for i := range values {
            valuePtrs[i] = &values[i]
        }
        
        if err := rows.Scan(valuePtrs...); err != nil {
            return nil, err
        }
        results = append(results, values)
    }
    
    return results, rows.Err()
}
```

### Input Validation

```go
func validateInputs(metric, window, output string) error {
    // Check metric type
    if _, ok := metricTypes[metric]; !ok {
        return fmt.Errorf("unknown metric: %s", metric)
    }
    
    // Parse window
    windowRegex := regexp.MustCompile(`^\d+[hdw]$`)
    if !windowRegex.MatchString(window) {
        return fmt.Errorf("invalid window format: %s", window)
    }
    
    // Check output extension
    if !strings.HasSuffix(output, ".svg") && !strings.HasSuffix(output, ".xlsx") {
        return errors.New("output must be .svg or .xlsx")
    }
    
    return nil
}
```

## Testing Approach

1. **Unit Tests** - Query building, data processing
2. **Integration Tests** - Database queries with test data
3. **End-to-End** - Chart generation validation
4. **Benchmarks** - Performance testing with `go test -bench`

## Current vs Future State

### Current Implementation
- Basic connectivity example
- Two hardcoded queries (temperature, health)
- Console output only

### Chart Generator Extension
- Command-line argument parsing
- Dynamic time windows
- Multiple output formats
- Error handling and validation

## Future Enhancements

1. **Real-time Updates** - WebSocket streaming with gorilla/websocket
2. **Interactive Dashboards** - Web UI with templates
3. **Batch Processing** - Generate multiple charts concurrently
4. **Query Builder** - Dynamic SQL generation
5. **Configuration Files** - YAML/JSON for chart templates