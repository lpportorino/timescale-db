# CLAUDE.md - TimescaleDB Tools Project

This file provides guidance to Claude when working with the TimescaleDB tools project.

## Project Structure

```
.
├── db/                    # Database infrastructure
│   ├── explore/          # Schema exploration tool (Python-based)
│   │   ├── timescaledb_report/  # Python package for report generation
│   │   └── run.py        # Main entry point
│   ├── save-restore/     # Backup and restore tools
│   ├── config/postgres/  # PostgreSQL configs
│   ├── mnt/db/postgres/  # Database data files
│   ├── backups/         # Backup storage
│   └── reports/          # Generated documentation (from explore)
│
├── example-app/          # Example application
│
├── docs/                 # Additional documentation
│   ├── QUICKSTART.md    # Quick start guide
│   ├── DOCKER_BASICS.md # Docker introduction
│   ├── TIMESCALEDB_INTRO.md # TimescaleDB basics
│   ├── LEARN_GO.md      # Go programming tutorial
│   └── TROUBLESHOOTING.md # Common issues & fixes
│
└── Root files
    ├── README.md         # User-facing documentation
    └── CLAUDE.md         # This file
```

## Design Philosophy

1. **Simplicity First** - Written for junior developers
2. **Docker Everything** - Consistent environment
3. **Makefile Interface** - Simple commands
4. **Self-Documenting** - Each directory has README and CLAUDE files

## Common Operations Flow

```bash
# Database management (all from db/ directory)
cd db
make start              # Start database (container starts empty)
make status             # Check if running
make restore BACKUP_DIR=backups/cluster_backup_20250704_165326  # Load sample data
make explore            # Generate documentation (works on empty or full DB)
make backup             # Create backup (shows progress)
make stop               # Stop database (data persists)

# Example application
cd ../example-app
make run                # Run example queries
```

## Workflow Insights from Testing

1. **Database starts empty** - Always restore from backup for sample data
2. **Restore requires confirmation** - Interactive prompt, use `echo "y" |` to automate
3. **Container IDs change** - Normal behavior due to `--rm` flag
4. **Explorer works on empty DB** - Generates report showing "0 tables" if no data
5. **Backup shows real progress** - Percentage updates in real-time
6. **Stop preserves data** - Only container is removed, not the data directory

## Critical Restore Lessons Learned

1. **Must remove backup_label and tablespace_map** - These files prevent proper startup
2. **Use correct TimescaleDB image** - Plain postgres:17 lacks required extensions
3. **WAL reset often needed** - pg_resetwal fixes "could not locate checkpoint" errors
4. **Special start command required** - `make start-restored` skips DB initialization
5. **File ownership matters** - postgres user is UID 999 in container
6. **Restore shows actual size** - "Restored size: 10.2GB" confirms success
7. **pg_resetwal permission errors** - Normal when run from outside container; the restore process handles WAL internally

## Key Design Decision: pg_basebackup

We use `pg_basebackup` instead of `pg_dump` because:
1. **No lock conflicts** - Works at file level, avoiding table lock timeouts
2. **Complete backup** - Gets entire cluster including all databases, users, settings
3. **Performance** - Much faster than logical dump/restore
4. **Reliability** - Can backup while autovacuum and TimescaleDB jobs are running

## Implementation Details

### save.py

**Architecture:**
- Uses `pg_basebackup` PostgreSQL utility via subprocess
- Progress reporting enabled by default (can disable with `--no-progress`)
- Tar format with compression level 6 by default
- Includes WAL files via streaming for consistency
- Tests connection and verifies REPLICATION permission

**Key features:**
- Estimates cluster size before backup
- Shows real-time progress during backup
- Creates timestamped backup directories
- Handles both tar and plain format outputs
- Comprehensive error handling

### restore_locally.py

**Architecture:**
- Local-only restoration (no network support)
- Must run as root (manages PostgreSQL service)
- Default data directory: `/mnt/db/postgres`
- Safely stops PostgreSQL before restore
- Backs up existing data directory
- Handles both tar and plain format backups
- Sets correct ownership and permissions

**Safety measures:**
- Requires confirmation unless `--force`
- Creates backup of existing data
- Dry run mode for testing
- Verifies prerequisites before starting

### db/explore (Python Implementation)

**Architecture:**
- Comprehensive Python-based schema exploration tool
- Uses psycopg2 for database connectivity
- Generates both Markdown and HTML reports
- Supports YAML/JSON configuration files
- Modular design with separate modules for different concerns

**Key features:**
- Complete schema documentation with table purposes
- TimescaleDB-aware (hypertables, continuous aggregates, policies)
- Performance metrics and index usage analysis
- Automatic detection of unused indexes
- Executive summary with health score
- HTML report with interactive navigation
- Supports custom connection parameters via CLI or config file
- Verbose logging mode for debugging

**Docker integration:**
- Runs as Docker container via db/Makefile
- Mounts reports directory for output
- Uses host network mode for simple connectivity
- Auto-builds image on first run

## Key Decisions

### Why This Structure?

1. **db/ consolidation** - All database-related tools in one place
2. **Single Makefile in db/** - All database operations from one place
3. **No docker-compose** - Makefiles are simpler for beginners
4. **Auto-build images** - Build on demand, not upfront
5. **Host network mode** - Avoids port mapping complexity
6. **Environment variables** - Standard configuration approach

### Makefile Pattern

Each Makefile follows the same pattern:
```makefile
.PHONY: help build run

# No colors for terminal compatibility

# Default shows help
help:
	@echo "Available commands..."

# Check prerequisites
check-db:
	@cd ../db && make check-running
```

### Debugging

```bash
# Test connection and permissions
psql -h sych.local -p 8094 -U jettison -c "SELECT rolreplication FROM pg_roles WHERE rolname = 'jettison'"

# Check pg_basebackup version
pg_basebackup --version

# Monitor backup progress
watch -n 1 'du -sh backups/cluster_backup_*'

# Verify backup contents
ls -la backups/cluster_backup_*/
```

## Implementation Guidelines

### Adding New Tools

1. **Create directory** in appropriate location
2. **Add Dockerfile** - Base on existing patterns
3. **Update db/Makefile** - Add new targets if needed
4. **Write README.md** - User documentation
5. **Write CLAUDE.md** - Technical details

### Docker Patterns

```dockerfile
# Standard base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

### Path Conventions (from db/ directory)

- Configs: `./config/postgres/`
- Data: `./mnt/db/postgres/`
- Backups: `./backups/`
- Reports: `./reports/`
- Tools: `./explore/`, `./save-restore/`

## Integration Points

### With Jettison System
- Backs up all TimescaleDB hypertables and continuous aggregates
- Preserves all system configuration and users
- Maintains data consistency across cluster

### With Development Workflow
- Fast backup/restore for testing
- Complete environment replication
- Version-locked restore (same PostgreSQL version required)

## Testing Guidelines

When testing changes:

1. **Backup testing:**
   - Test with small and large clusters
   - Verify tar and plain formats
   - Check compression levels
   - Test progress reporting

2. **Restore testing:**
   - Test on clean system
   - Test with existing data
   - Verify service management
   - Check permission setting

3. **Error scenarios:**
   - Missing REPLICATION permission
   - Disk space issues
   - Service management failures
   - Wrong PostgreSQL version

## Performance Considerations

1. **Backup performance:**
   - Compression level affects speed/size tradeoff
   - Plain format faster but uses more space
   - Network speed critical for remote backups

2. **Restore performance:**
   - Tar extraction can be CPU intensive
   - Service stop/start adds overhead
   - Permission setting is recursive (can be slow)

## Security Notes

1. **Credentials:**
   - Password in script (consider .pgpass)
   - REPLICATION permission required
   - Root access for restore

2. **Backup security:**
   - Contains all database data
   - Should be encrypted for storage
   - Excluded from git

3. **Network:**
   - Uses PostgreSQL native encryption
   - Firewall considerations for port 8094

## Common Issues

### "make: command not found"
- Ubuntu: `sudo apt install make`
- Explanation: Make is not installed by default on minimal systems

### "Cannot connect to Docker"
- Add user to docker group: `sudo usermod -aG docker $USER`
- Logout and login again
- Test: `docker ps`

### "Database not running"
- Always check: `cd db && make status`
- Start if needed: `cd db && make start`
- Logs: `docker logs timescaledb-local`

### System Environment Messages
- "Start Hyprland with command Hyprland" - System message, safe to ignore
- Appears in command output but doesn't affect functionality

### Backup Sizes
- Sample backup with data: ~1.2GB
- Empty database backup: ~4.9MB
- Size difference = actual time-series data

## Testing Approach

1. **Unit Level** - Test individual scripts
2. **Integration** - Test tool combinations
3. **End-to-End** - Full workflow testing
4. **Documentation** - Verify all examples work

## Security Considerations

1. **Credentials** - Use .env files, never commit
2. **Network** - Host mode is for development only
3. **Volumes** - Read-only where possible
4. **Privileges** - Only restore needs privileged mode

## Practical Implementation Tips

### Running the Full Workflow
1. Always start with `make status` to check current state
2. The database directory (`mnt/db/postgres/`) persists between container restarts
3. Each tool builds its Docker image on first run (cached thereafter)
4. Use `make help` liberally - it's implemented in every directory

### Docker Behavior
- Containers use `--rm` flag for automatic cleanup
- Images are built with `--rm` to avoid intermediate layer buildup
- Host network mode means no port mapping complexities
- All tools run as root inside containers (needed for permissions)

### File Permissions
- Reports generated by tools may be owned by root
- This is expected due to Docker container execution
- Use `sudo chown -R $USER:$USER reports/` if needed

### Performance Observations
- First `make start` takes longer (pulling image)
- Subsequent starts are fast (~1-2 seconds)
- Backup/restore speed depends on data size and disk I/O
- Explorer runs quickly even on large schemas

## Chart Generation Task Details

### Overview

The example application serves as a template for building a chart generator that creates visualizations from TimescaleDB data.

### Requirements for Chart Generator

1. **Command-line arguments:**
   - `--metric` - Type of metric (temperature, health, power)
   - `--window` - Time window (1h, 24h, 7d)
   - `--output` - Output file path (.svg or .xlsx)

2. **Data sources:**
   - Temperature: `meteo_metrics` table
   - Health: `health_metrics_1min_cagg` table
   - Power: `power_metrics` table

3. **Output formats:**
   - SVG: Use matplotlib for charts
   - Excel: Use openpyxl with embedded charts

### Key Tables and Queries

#### Temperature Data
```sql
SELECT time, station, temperature, humidity, pressure
FROM meteo_metrics
WHERE time >= NOW() - INTERVAL '24 hours'
ORDER BY time, station;
```

#### Health Metrics
```sql
SELECT time, service, category, avg_health, min_percentage, max_percentage
FROM health_metrics_1min_cagg
WHERE time >= NOW() - INTERVAL '1 hour'
ORDER BY time, service, category;
```

#### Power Consumption
```sql
SELECT time, service_name, channel, voltage, current, power
FROM power_metrics
WHERE time >= NOW() - INTERVAL '6 hours'
ORDER BY time, service_name;
```

### Implementation Approach

1. **Parse time windows:** Convert "1h", "24h", "7d" to PostgreSQL intervals
2. **Handle historical data:** Query actual time ranges in the backup
3. **Generate appropriate charts:**
   - Temperature: Line chart with multiple stations
   - Health: Percentage chart (0-100%) by service
   - Power: Stacked/grouped by service

### Testing the Implementation

```bash
# Different time windows
python chart_generator.py --metric temperature --window 1h
python chart_generator.py --metric temperature --window 24h
python chart_generator.py --metric temperature --window 7d

# Different output formats
python chart_generator.py --metric health --window 1h --output chart.svg
python chart_generator.py --metric power --window 24h --output data.xlsx

# Error cases
python chart_generator.py --metric invalid --window 1h  # Invalid metric
python chart_generator.py --metric temperature --window 1000d  # No data
```