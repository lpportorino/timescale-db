# 🔧 Troubleshooting Guide - Fix Common Issues!

> **Something not working?** Don't worry! This guide covers 99% of issues beginners face. Let's get you back on track!

## 📚 Table of Contents

1. [Quick Fixes (Try These First!)](#-quick-fixes-try-these-first)
2. [Docker Issues](#-docker-issues)
3. [Database Problems](#-database-problems)
4. [Go/Build Errors](#-gobuild-errors)
5. [Data & Query Issues](#-data--query-issues)
6. [System-Specific Problems](#-system-specific-problems)
7. [Still Stuck?](#-still-stuck)

## 🚑 Quick Fixes (Try These First!)

Before diving into specific issues, try these common fixes:

```bash
# 1. Check Docker is running
docker --version
docker ps

# 2. Check you're in the right directory
pwd  # Should show .../timescaledb-tools/db or similar

# 3. Check database status
cd db
make status

# 4. Restart everything
make stop
make start

# 5. Check for error messages
docker logs timescaledb-local
```

## 🐳 Docker Issues

### "Cannot connect to Docker daemon"

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solutions:**

1. **Check if Docker is running:**
   ```bash
   # Linux
   sudo systemctl status docker
   sudo systemctl start docker
   
   # Mac/Windows
   # Make sure Docker Desktop is running (check system tray)
   ```

2. **Add yourself to docker group (Linux):**
   ```bash
   sudo usermod -aG docker $USER
   # Then logout and login, OR run:
   newgrp docker
   ```

3. **Permission denied even after adding to group:**
   ```bash
   # Check your groups
   groups
   
   # If docker not listed, the change hasn't taken effect
   # Try: logout completely and login again
   # Or restart your computer
   ```

### "Port already allocated"

**Symptoms:**
```
bind: address already in use
```

**Solutions:**

1. **Find what's using the port:**
   ```bash
   # Linux/Mac
   lsof -i :8094
   
   # Windows (run as admin)
   netstat -ano | findstr :8094
   ```

2. **Stop the conflicting process or use different port:**
   ```bash
   # Edit db/Makefile and change 8094 to something else
   # For example, change to 8095
   ```

### "No space left on device"

**Symptoms:**
```
no space left on device
```

**Solutions:**

1. **Check Docker space usage:**
   ```bash
   docker system df
   ```

2. **Clean up Docker:**
   ```bash
   # Remove stopped containers
   docker container prune
   
   # Remove unused images
   docker image prune -a
   
   # Remove everything unused (careful!)
   docker system prune -a --volumes
   ```

3. **Check disk space:**
   ```bash
   df -h
   ```

## 🗄️ Database Problems

### "Database is not running"

**Symptoms:**
```
✗ Database is not running
```

**Solutions:**

1. **Start the database:**
   ```bash
   cd db
   make start
   ```

2. **Check if it crashed:**
   ```bash
   docker ps -a | grep timescaledb
   docker logs timescaledb-local
   ```

3. **Common crash reasons:**
   - Not enough memory (need at least 2GB free)
   - Corrupted data directory
   - Port conflict

### "PANIC: could not locate a valid checkpoint record"

**Symptoms:**
```
PANIC: could not locate a valid checkpoint record
```

**This happens after restore!** Solutions:

1. **Reset the WAL (Write-Ahead Log):**
   ```bash
   # Stop database
   make stop
   
   # Reset WAL
   docker run --rm -u postgres \
     -v $(pwd)/mnt/db/postgres:/var/lib/postgresql/data \
     timescale/timescaledb:latest-pg17 \
     pg_resetwal -f /var/lib/postgresql/data
   
   # Start with restored data
   make start-restored
   ```

### "Connection refused"

**Symptoms:**
```
could not connect to server: Connection refused
```

**Solutions:**

1. **Check database is running:**
   ```bash
   make status
   ```

2. **Check network settings:**
   ```bash
   # Should show port 8094
   docker port timescaledb-local
   ```

3. **Try connecting directly:**
   ```bash
   docker exec timescaledb-local psql -U jettison -d jettison -c "SELECT 1"
   ```

## 🔨 Go/Build Errors

### "go: command not found"

**Symptoms:**
```
/bin/sh: go: not found
```

**Solutions:**

1. **You don't need Go installed!** Our Docker setup handles it.

2. **If you want to modify code locally:**
   ```bash
   # Install Go from https://go.dev/dl/
   # Then verify:
   go version
   ```

### "missing go.sum entry"

**Symptoms:**
```
missing go.sum entry for module
```

**Solutions:**

1. **The go.sum file might be missing/corrupted:**
   ```bash
   cd db/save-restore
   go mod download
   go mod tidy
   ```

2. **Or just rebuild the Docker image:**
   ```bash
   docker rmi timescaledb-save-restore
   make backup  # This will rebuild
   ```

### Build takes forever

**Symptoms:**
- Docker build hangs
- Very slow compilation

**Solutions:**

1. **Check Docker resources (Docker Desktop):**
   - Settings → Resources
   - Increase CPU and Memory limits

2. **Use build cache:**
   ```bash
   # Don't use --no-cache unless necessary
   docker build -t myimage .
   ```

## 📊 Data & Query Issues

### "No data showing" in example app

**Symptoms:**
- Example app runs but shows no data
- "No temperature data found"

**THIS IS THE #1 ISSUE!** The sample data is from July 2025!

**Solutions:**

1. **Check what dates have data:**
   ```bash
   cd db
   docker exec timescaledb-local psql -U jettison -d jettison -c \
     "SELECT MIN(time), MAX(time) FROM meteo_metrics"
   ```

2. **The data is from July 2-4, 2025!** Queries for "NOW()" won't work.

3. **Use specific dates in queries:**
   ```sql
   -- Instead of: WHERE time >= NOW() - INTERVAL '24 hours'
   -- Use: WHERE time >= '2025-07-04' AND time < '2025-07-05'
   ```

### "ORDER/GROUP BY expression not found in targetlist"

**Symptoms:**
```
ERROR: ORDER/GROUP BY expression not found in targetlist
```

**Solutions:**

1. **This is a SQL error. Check your query:**
   ```sql
   -- Wrong:
   SELECT service, time FROM table ORDER BY category
   
   -- Right (include all ORDER BY columns in SELECT):
   SELECT service, time, category FROM table ORDER BY category
   ```

### Restore creates huge backup files

**Symptoms:**
- Backup directory fills up disk
- Multiple backup attempts

**Solutions:**

1. **Clean old backups:**
   ```bash
   cd db
   ls -la backups/
   # Remove old ones (keep the original!)
   rm -rf backups/cluster_backup_20250706_*
   ```

2. **Backup is ~1GB compressed, ~10GB uncompressed** - this is normal!

## 💻 System-Specific Problems

### macOS: "Cannot install postgresql-client"

**Solutions:**

1. **Use Homebrew:**
   ```bash
   brew install postgresql
   ```

2. **Or use Docker version (recommended)** - our setup handles it!

### Windows: "make: command not found"

**Solutions:**

1. **Use Git Bash** (comes with Git for Windows)

2. **Or use WSL2** (Windows Subsystem for Linux):
   ```powershell
   wsl --install
   # Then use Ubuntu terminal
   ```

3. **Or install Make for Windows:**
   - Download from: http://gnuwin32.sourceforge.net/packages/make.htm

### Windows: Path issues

**Symptoms:**
```
Error: no such file or directory
```

**Solutions:**

1. **Use forward slashes in paths:**
   ```bash
   # Wrong: C:\Users\me\project
   # Right: /c/Users/me/project (in Git Bash)
   ```

2. **Use WSL2 for better compatibility**

## 🎯 Common Makefile Errors

### "make: *** No rule to make target"

**Solutions:**

1. **You're in the wrong directory:**
   ```bash
   pwd  # Check where you are
   ls   # Should see Makefile
   ```

2. **Correct directory structure:**
   ```
   timescaledb-tools/
   ├── db/           # Run database commands here
   ├── example-app/  # Run example commands here
   └── docs/         # Documentation
   ```

### Variables not substituting

**Symptoms:**
```
Error: invalid argument "host=$${PGHOST:-sych.local}"
```

**Solutions:**

1. **Make sure you're using Make, not running Docker directly**

2. **Check Make version:**
   ```bash
   make --version  # Should be 3.81 or higher
   ```

## 🔍 Debugging Commands

### Useful debugging commands:

```bash
# Check all Docker containers
docker ps -a

# Check specific container logs
docker logs timescaledb-local --tail 50

# Check disk usage
df -h
docker system df

# Check what's listening on ports
# Linux/Mac:
netstat -tlnp | grep 8094
lsof -i :8094

# Windows:
netstat -an | findstr 8094

# Test database connection
docker exec timescaledb-local pg_isready

# Check database tables
docker exec timescaledb-local psql -U jettison -d jettison \
  -c "\dt"

# Check data date ranges
docker exec timescaledb-local psql -U jettison -d jettison \
  -c "SELECT MIN(time), MAX(time), COUNT(*) FROM meteo_metrics"
```

## 📝 Log Files to Check

1. **Docker logs:**
   ```bash
   docker logs timescaledb-local > db.log
   ```

2. **Build logs:**
   ```bash
   docker build . --progress=plain 2>&1 | tee build.log
   ```

3. **System logs:**
   ```bash
   # Linux
   journalctl -u docker -n 100
   
   # Mac
   /Applications/Utilities/Console.app
   # Search for: docker
   ```

## 🆘 Still Stuck?

If none of the above helps:

1. **Collect information:**
   ```bash
   # Save this output:
   docker --version
   docker ps -a
   cd db && make status
   docker logs timescaledb-local --tail 100
   ```

2. **Check existing issues:**
   - Look for similar problems in GitHub issues
   - Search error messages

3. **Ask for help:**
   - Create a new issue with:
     - What you tried to do
     - Exact error message
     - Output from step 1
     - Your OS (Windows/Mac/Linux)

4. **Common info to include:**
   ```bash
   # System info
   uname -a  # Linux/Mac
   ver       # Windows
   
   # Docker info
   docker version
   docker info
   
   # Disk space
   df -h
   
   # Memory
   free -h   # Linux
   ```

## 💡 Prevention Tips

1. **Always check you're in the right directory**
2. **Read error messages carefully** - they usually tell you what's wrong
3. **Keep notes** of what works for future reference
4. **Clean up regularly** with `docker system prune`
5. **Don't skip the restore step** - database starts empty!
6. **Remember the data dates** - July 2025!

---

**Remember:** Everyone encounters errors when learning. The key is to:
- Read the error message
- Try the quick fixes
- Check this guide
- Ask for help if needed

You're doing great! 🌟

*Back to [README](../README.md) | Questions? Create an issue!*
