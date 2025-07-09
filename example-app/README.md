# 📊 Example TimescaleDB Application

> **What's this?** A simple Go app that shows you how to query time-series data from TimescaleDB. Perfect for learning!

## 🎯 What You'll See

When you run this app, it queries:
- 🌡️ **Temperature readings** from weather stations  
- 💚 **Health scores** from system services
- ⚡ **Power consumption** data (if you extend it)

## 🚀 Quick Start

```bash
# Make sure database is running first!
cd ../db
make status

# Now run the example
cd ../example-app
make run
```

You'll see output like:
```
🌡️ Temperature Data:
2025-07-04 01:00:00 | Weather_Station_3 | 22.84°C | 51.23%
2025-07-04 01:00:00 | Weather_Station_2 | 23.45°C | 49.87%

💚 Health Metrics:
2025-07-04 00:59:00 | gateway | http | Health: 99.50%
```

## 📂 How It Works

The app (`main.go`) does three things:

1. **Connects to the database** using these settings:
   ```go
   host:     "sych.local"    // or localhost
   port:     "8094"
   user:     "jettison"
   password: "aMvzpGPgNVtH53S"
   database: "jettison"
   ```

2. **Runs SQL queries** to get data:
   ```sql
   -- Get temperature readings
   SELECT time, station, temperature, humidity
   FROM meteo_metrics
   WHERE time >= '2025-07-04 00:00:00'
   ORDER BY time DESC
   ```

3. **Shows the results** in a nice format

## 📊 Available Data Tables

### 🌡️ Weather Data (`meteo_metrics`)
```sql
time        | station           | temperature | humidity | pressure
2025-07-04  | Weather_Station_1 | 22.5°C     | 45%      | 1013.2
```

### 💚 Health Metrics (`health_metrics_1min_cagg`)
```sql
time        | service | category | avg_health | min_percentage | max_percentage
2025-07-04  | web     | http     | 99.5%      | 98.2%         | 100%
```

### ⚡ Power Usage (`power_metrics`)
```sql
time        | service_name | channel | voltage | current | power
2025-07-04  | server_1     | main    | 220V    | 2.5A    | 550W
```

## 🛠️ Modify the Code!

### Try These Changes

1. **Change the time range** in `main.go`:
   ```go
   // Instead of just 1 hour:
   WHERE time >= '2025-07-04 00:00:00' AND time <= '2025-07-04 01:00:00'
   
   // Try the whole day:
   WHERE time >= '2025-07-04 00:00:00' AND time <= '2025-07-04 23:59:59'
   ```

2. **Add a new query** for power data:
   ```go
   // Add this to main.go
   query := `
       SELECT time, service_name, power
       FROM power_metrics
       WHERE time >= '2025-07-04 00:00:00'
       ORDER BY power DESC
       LIMIT 10
   `
   ```

3. **Filter by specific station**:
   ```go
   WHERE station = 'Weather_Station_1'
   AND time >= '2025-07-04 00:00:00'
   ```

## 🎯 Build Your Own App!

### Step 1: Copy This Directory
```bash
cp -r example-app my-awesome-app
cd my-awesome-app
```

### Step 2: Add New Features

**Example: Find the Hottest Hour**
```go
query := `
    SELECT 
        date_trunc('hour', time) as hour,
        MAX(temperature) as max_temp,
        MIN(temperature) as min_temp
    FROM meteo_metrics
    WHERE time >= '2025-07-04'
    GROUP BY hour
    ORDER BY max_temp DESC
    LIMIT 1
`
```

### Step 3: Add Command-Line Arguments
```go
import "flag"

metric := flag.String("metric", "temperature", "Type of metric")
window := flag.String("window", "1h", "Time window")
flag.Parse()
```

## 🔌 Environment Variables

You can change database settings:

```bash
# Use different host
export PGHOST=localhost

# Use different port
export PGPORT=5432

# Then run
make run
```

## 🚨 Troubleshooting

### "Connection refused"
```bash
# Database not running?
cd ../db
make status
make start  # If needed
```

### "No data returned"
Remember: The data is from **July 2025**! Try these dates:
- `2025-07-02` to `2025-07-04`

### Want to see the code?
```bash
# Look at the Go code
cat main.go

# Edit it
nano main.go  # or use your favorite editor
```

## 📚 Learning Resources

- 🎮 **[Go Playground](https://go.dev/play/)** - Try Go code online
- 📘 **[Go by Example](https://gobyexample.com/)** - Learn Go patterns
- 📊 **[TimescaleDB Docs](https://docs.timescale.com/)** - Time-series SQL

## 🎉 What's Next?

1. **Modify the queries** - Try different time ranges
2. **Add new features** - Query different tables
3. **Build a chart generator** - Visualize the data
4. **Create a monitoring dashboard** - Real-time updates

---

**Remember:** This is just a starting point. Copy it, modify it, make it yours! 🚀

*Questions? Check [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) or create an issue!*