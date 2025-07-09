# CLAUDE.md - Database Directory

## Overview

This directory manages the TimescaleDB instance used by all other tools. It provides:
- Database lifecycle management (start/stop)
- Backup and restore functionality
- Configuration management

## Key Design Decisions

### Docker-based Deployment
- Uses official TimescaleDB image
- Host network mode for simplicity
- Data persisted in local volumes

### Directory Structure
- `config/postgres/` - Config files (pg_hba.conf, postgresql.conf)
- `mnt/db/postgres/` - Actual database files
- `backups/` - Backup storage

### Makefile-driven Interface
- Simple commands for junior developers
- Built-in safety checks
- Colored output for clarity

## Implementation Notes

### Database Container
- Name: `timescaledb-local`
- Image: `timescale/timescaledb:latest-pg15`
- Network: host mode (no port mapping needed)
- Volumes: Bind mounts for data and config
- Auto-removal: Uses `--rm` flag to clean up on stop
- Init process: Container ID changes on each start (expected behavior)

### Tool Integration
- All tools run via Docker containers
- Explorer outputs to `reports/` directory
- Backups stored in `backups/` directory
- Images built automatically if missing
- Docker images use `--rm` flag for automatic cleanup
- Tools run as root inside containers (needed for file permissions)

## Common Tasks

### Adding Configuration
1. Place config files in `config/postgres/`
2. Restart database: `make stop && make start`
3. Config is mounted read-only into container

### Changing Credentials
1. Stop database: `make stop`
2. Clean data: `rm -rf mnt/db/postgres/*`
3. Edit Makefile with new credentials
4. Start fresh: `make start`

### Debugging Connection Issues
```bash
# Test connection
docker exec timescaledb-local psql -U jettison -d jettison -c "SELECT 1"

# Check logs
docker logs timescaledb-local

# Inspect container
docker inspect timescaledb-local
```

## Integration Points

### With Other Tools
- All tools expect database on port 8094
- Use environment variables for configuration
- Database must be running for most operations

### File Paths
- Explorer reports: `./reports/`
- Backup storage: `./backups/`
- Database data: `./mnt/db/postgres/`
- Config files: `./config/postgres/`

## Security Considerations

1. **Credentials**: Hardcoded in Makefile (for dev only)
2. **Network**: Host mode exposes port directly
3. **Volumes**: Data files have PostgreSQL permissions

## Observed Behavior and Timing

### Startup Times
- Database container start: ~1-2 seconds
- Database ready for connections: ~5 seconds
- First connection may take longer due to initialization

### Backup Performance
- Small database (4.9MB): ~1 second
- Large database (1.2GB): Varies by disk speed
- Progress reporting shows real-time percentage
- Compression reduces size significantly

### Restore Process
- Stops existing database gracefully
- Clears data directory completely
- Extracts backup (tar format)
- Restarts with new data
- Total time: 10-30 seconds depending on backup size

### Explorer Tool
- Generates reports even for empty databases
- HTML report includes interactive elements
- Markdown report is plain text for version control
- Runs in ~1-2 seconds

## System Messages
- "Start Hyprland with command Hyprland": System environment message, can be ignored
- Container IDs in output: Normal, changes each run due to `--rm` flag

## Future Improvements

- Support for .env file configuration
- Health check integration
- Automatic backup scheduling
- SSL/TLS configuration
- Connection pooling setup
- Backup encryption for sensitive data
- Incremental backup support