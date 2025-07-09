# 🗄️ Database Directory - Your TimescaleDB Home!

> **What's this?** This folder manages your time-series database. Think of it as mission control for all your data!

## 📁 What's Inside?

```
db/
├── 📋 Makefile           # All your commands (type 'make help')
├── 📁 config/postgres/   # Database settings
├── 💾 mnt/db/postgres/   # Your actual data (10GB+ when restored!)
├── 🗂️ backups/          # Saved database snapshots (~1GB each)
├── 📊 reports/          # Database documentation (generated)
├── 🔍 explore/          # Tool to see what's in your database
└── 💼 save-restore/     # Backup and restore tools
```

## 🚀 Quick Start - Your First Database!

### Step 1: Start Your Database (30 seconds)

```bash
# Start TimescaleDB
make start

# Make sure it's running
make status
```

✅ You should see: `Database is running`

### Step 2: Load Sample Data (2 minutes)

> **Important!** The database starts empty. You need to restore data to see anything!

```bash
# See what backups are available
make list-backups

# Restore the sample data (type 'y' when asked)
make restore BACKUP_DIR=backups/cluster_backup_20250704_165326
```

📊 **What's happening?**
- Extracting ~1GB backup → 10GB of sensor data
- You'll see progress: `Extracted 1000/3917 files...`
- Final message: `Restored size: 10.2GB`

### Step 3: Explore Your Data! (1 minute)

```bash
# Generate a report of what's in your database
make explore

# Look at the report (open in browser)
open reports/timescaledb_schema.html
# Or on Linux: xdg-open reports/timescaledb_schema.html
```

🎉 **You now have:**
- 18 tables of time-series data
- 3 days of sensor readings (July 2-4, 2025)
- Temperature, health, and power metrics!

### Step 4: See It In Action!

```bash
# Go to the example app
cd ../example-app

# Run it!
make run
```

You'll see real sensor data from the database! 🎊

## 📋 Database Details

### How to Connect
```
Host:     sych.local (or localhost)
Port:     8094
Database: jettison
Username: jettison
Password: aMvzpGPgNVtH53S
```

### What's in the Sample Data?

📦 **Backup Size:** 1.2GB compressed → 10.2GB when restored!

📊 **Data Includes:**
- 🌡️ **Weather Data** (`meteo_metrics`) - Temperature, humidity from 20 stations
- ⚡ **Power Usage** (`power_metrics`) - Energy consumption metrics
- 💚 **Health Monitoring** (`health_metrics_raw`) - Service health scores
- 🚨 **System Alerts** (`alerts`) - Warning and error logs
- 📝 **And much more!** - 18 tables total

## 🛠️ Common Tasks

### Daily Commands

```bash
# Check if database is running
make status

# Start the database
make start

# Stop the database (data is preserved!)
make stop

# Create a backup
make backup
# You'll see: "Backing up: 75% (750/1000 MB)"

# See all available commands
make help
```

### 💡 Pro Tips

1. **Always backup before big changes!**
   ```bash
   make backup    # Creates timestamped backup
   ```

2. **Database won't start?**
   ```bash
   make status    # Check current state
   make stop      # Stop if needed
   make start     # Fresh start
   ```

3. **Want to start fresh?**
   ```bash
   make clean     # ⚠️ WARNING: Deletes everything!
   make start     # Start empty
   make restore BACKUP_DIR=backups/...  # Restore data
   ```

## 🚨 Troubleshooting

### "Could not locate a valid checkpoint record"

This happens after restore. Here's the fix:

```bash
# 1. Stop database
make stop

# 2. Reset the WAL (Write-Ahead Log)
docker run --rm -u postgres \
  -v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
  timescale/timescaledb:latest-pg17 \
  pg_resetwal -f /var/lib/postgresql/data

# 3. Start with restored data
make start-restored
```

### Database Empty After Restore?

Use the right start command:
- ✅ `make start-restored` - After restoring
- ❌ `make start` - This creates a NEW empty database!

### Permission Errors?

This is normal! Database files are owned by the postgres user.

### "Device or resource busy" during restore?

This happens when the data directory is still mounted. The restore process now handles this automatically:
- Force removes the container
- Waits for cleanup
- Clears the directory with sudo

If you still see this error, wait a few seconds and try again.

### Need More Help?

Check [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) for complete solutions!

## 🎓 Advanced Usage

### Connect with SQL Client

```bash
# Quick connection
docker exec -it timescaledb-local psql -U jettison -d jettison

# Try these commands:
\dt                                    # List all tables
SELECT COUNT(*) FROM meteo_metrics;    # Count weather readings
SELECT * FROM meteo_metrics LIMIT 5;   # See sample data
\q                                     # Exit
```

### Custom Backup Options

```bash
# High compression (slower but smaller)
make backup COMPRESS=9

# Quick backup (less compression)
make backup COMPRESS=1
```

## 💾 Space Requirements

- **Empty database:** ~50MB
- **With sample data:** ~10.2GB
- **Each backup:** ~1.2GB
- **During restore:** Need 2x space temporarily

## 📑 Complete Command Reference

```bash
make help          # Show all available commands
make status        # Check if database is running
make start         # Start fresh empty database
make stop          # Stop database (preserves data)
make backup        # Create timestamped backup
make list-backups  # List all available backups
make restore BACKUP_DIR=backups/...  # Restore from backup
make explore       # Generate database documentation
make clean         # ⚠️ DELETE EVERYTHING - be careful!
```

## 🎯 Remember

1. **Database starts empty** - Always restore to get data
2. **Backups are important** - Run before major changes
3. **Data persists** - Stopping doesn't delete data
4. **Sample data is from July 2025** - Queries need correct dates

---

**Ready to explore more?** Check out the [example app](../example-app) to see how to query this data!

*Questions? See [TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) or create an issue!*
