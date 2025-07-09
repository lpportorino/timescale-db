# ⚡ Quick Start Guide - Get Running in 5 Minutes!

> **In a hurry?** This guide gets you from zero to working database with real data in just 5 minutes. Let's go!

## 🎯 What We're Doing

We're going to:
1. ✅ Start a time-series database
2. ✅ Load it with real sensor data  
3. ✅ See the data in action
4. ✅ Understand what just happened

## 🚀 Let's Go! (Copy & Paste These)

### Step 1: Start the Database (30 seconds)

```bash
# Go to the database folder
cd db

# Start TimescaleDB
make start
```

You should see:
```
✓ Database started successfully
Container: timescaledb-local
```

### Step 2: Load Sample Data (2 minutes)

```bash
# Restore the sample backup (type 'y' when asked)
echo "y" | make restore BACKUP_DIR=backups/cluster_backup_20250704_165326
```

You'll see progress like:
```
Extracting backup files...
Restoring database...
✓ Restore completed successfully!
```

### Step 3: See Your Data! (30 seconds)

```bash
# Go to the example app
cd ../example-app

# Run it!
make run
```

You should see real data:
```
🌡️ Temperature Data:
2025-07-04 01:00:00 | Weather_Station_3 | 22.84°C | 51.23%
2025-07-04 01:00:00 | Weather_Station_2 | 23.45°C | 49.87%
...

💚 Health Metrics:
2025-07-04 00:59:00 | gateway | http | Health: 99.50%
2025-07-04 00:59:00 | gateway | grpc | Health: 99.20%
...
```

## 🎉 Congratulations!

You just:
- Started a **TimescaleDB** database (PostgreSQL for time-series)
- Loaded **10GB of sensor data** from July 2025
- Queried **temperature** and **health metrics**

## 📊 What's in the Database?

The sample data includes:
- 🌡️ **Weather stations** - Temperature, humidity, pressure readings
- 💚 **Service health** - System monitoring metrics
- ⚡ **Power consumption** - Energy usage data
- 📈 **All from July 2-4, 2025** - Three days of data

## 🔍 Explore More (2 minutes)

### See Database Schema

```bash
cd ../db
make explore
```

Then open `reports/timescaledb_schema.html` in your browser!

### Try Different Queries

Edit `example-app/main.go` and change the date range:
```go
// Change this line:
WHERE time >= '2025-07-04 00:00:00' AND time <= '2025-07-04 01:00:00'

// To this (get more data):
WHERE time >= '2025-07-02 00:00:00' AND time <= '2025-07-04 23:59:59'
```

Then run again:
```bash
make run
```

## 🛑 Stop Everything

When you're done exploring:

```bash
cd ../db
make stop
```

This stops the container but **keeps your data** for next time!

## 💡 Quick Tips

### See if Database is Running
```bash
cd db
make status
```

### View Database Logs
```bash
docker logs timescaledb-local --tail 20
```

### Connect Directly to Database
```bash
docker exec -it timescaledb-local psql -U jettison -d jettison
```

Then try:
```sql
-- Count temperature readings
SELECT COUNT(*) FROM meteo_metrics;

-- See latest readings
SELECT * FROM meteo_metrics ORDER BY time DESC LIMIT 5;

-- Exit
\q
```

## 🚫 Common Issues

### "Cannot connect to Docker"
```bash
# Make sure Docker is running
docker --version
docker ps
```

### "No data showing"
Remember: The data is from **July 2025**, not today! The queries look for specific dates.

### "Database not running"
```bash
cd db
make status  # Check status
make start   # Start it
```

## 🎯 What's Next?

Now that you have a working system:

1. **Learn the Basics**
   - [DOCKER_BASICS.md](DOCKER_BASICS.md) - Understand containers (30 min)
   - [TIMESCALEDB_INTRO.md](TIMESCALEDB_INTRO.md) - Time-series databases (20 min)
   - [LEARN_GO.md](LEARN_GO.md) - Go programming basics (45 min)

2. **Build Something**
   - Modify the example app
   - Add new queries
   - Create visualizations

3. **Experiment**
   - Try the backup tool
   - Explore the schema
   - Write your own data

## 🎊 You Did It!

In just 5 minutes you:
- ✅ Set up a production-grade time-series database
- ✅ Loaded millions of data points
- ✅ Ran real queries on real data
- ✅ Learned the basic commands

**That's impressive!** Most people take hours to get this far. 🌟

---

**Ready for more?** Head back to the [main README](../README.md) for the full learning path!

*Remember: If something doesn't work, check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - we've got you covered!*