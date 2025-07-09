# TimescaleDB Backup and Restore Tools

Physical backup and restore tools using PostgreSQL's `pg_basebackup` utility. These tools create complete cluster backups that preserve all databases, users, settings, and TimescaleDB-specific objects.

## Why Physical Backups?

We use `pg_basebackup` (physical backups) instead of `pg_dump` (logical backups) because:
- **No lock conflicts** - Works at file level, avoiding table lock timeouts with TimescaleDB continuous aggregates
- **Complete backup** - Captures entire PostgreSQL cluster including all databases, users, and settings
- **Faster** - Direct file copy is much faster than logical export/import
- **Reliable** - Can backup while autovacuum and TimescaleDB background jobs are running

## Quick Start

### Creating a Backup

From the `db/` directory:
```bash
make backup
```

This creates a timestamped backup in `db/backups/cluster_backup_YYYYMMDD_HHMMSS/`

### Restoring from Backup

From the `db/` directory:
```bash
# List available backups
make list-backups

# Restore a specific backup
make restore BACKUP_DIR=backups/cluster_backup_20250704_165326
```

**⚠️ Warning**: Restore will completely replace your current database with the backup!

## Backup Details

### What Gets Backed Up

- All databases in the PostgreSQL cluster
- All users and roles
- All configuration settings
- All TimescaleDB hypertables and continuous aggregates
- All data (compressed ~1GB from ~10GB uncompressed)

### Backup Format

Backups are created in tar format with compression:
- `base.tar.gz` - Main database files
- `pg_wal.tar.gz` - Write-ahead logs for consistency
- `backup_manifest` - Backup metadata

### Backup Size Example

- Compressed backup: ~1.2GB (with compression level 6)
- Uncompressed database: ~10.2GB
- Compression ratio: ~10:1

## Restore Process - What Actually Happens

### Step-by-Step Process

1. **Stops the running database** - Ensures no conflicts
2. **Clears existing data** - Removes all current database files
3. **Extracts backup** - Unpacks compressed tar files with progress reporting
4. **Sets permissions** - Ensures PostgreSQL can access files (postgres:postgres)
5. **Removes recovery files** - Cleans up `backup_label` and `tablespace_map`
6. **Starts database** - Uses TimescaleDB image without initialization

### Critical Requirements

- Restore requires the **same PostgreSQL major version** (17.x)
- Must use TimescaleDB image for extension support
- First startup after restore may take 15-20 seconds
- WAL reset may be needed if restore fails

### Common Restore Issues and Solutions

#### Issue: "could not locate a valid checkpoint record"

This happens when WAL files are inconsistent. Solution:
```bash
# Stop the failed container
make stop

# Reset the WAL (safe after pg_basebackup restore)
docker run --rm -u postgres -v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
    timescale/timescaledb:latest-pg17 pg_resetwal -f /var/lib/postgresql/data

# Start with restored data
make start-restored
```

#### Issue: Database appears empty after restore

The container may be reinitializing. Ensure you're using `make start-restored` which skips initialization.

#### Issue: Permission denied errors

The restore process sets ownership to UID/GID 999 (postgres user in container). This is normal.

## Implementation Details

### save.py

Creates backups using `pg_basebackup`:
- Tests connection and verifies REPLICATION permission
- Estimates cluster size before backup
- Shows real-time progress percentage
- Creates timestamped backup directories
- Uses tar format with compression level 6
- Includes streaming WAL for consistency

### restore_docker.py

Restores backups inside Docker container:
- Clears existing data directory completely
- Extracts tar files with file count progress
- Shows "Extracted X/Y files..." during restore
- Sets ownership to postgres:postgres (UID/GID 999)
- Removes `backup_label` and `tablespace_map` files
- Reports final size (e.g., "Restored size: 10.2GB")

## Complete Workflow Example

```bash
# 1. Navigate to database directory
cd db

# 2. Check current database status
make status
# Output: ✓ Database is running

# 3. Create a backup
make backup
# Output shows progress:
# Backing up: 100% (1234/1234 MB)
# ✓ Backup completed
# Location: backups/cluster_backup_20250706_152000

# 4. List available backups
make list-backups
# Shows all backups with sizes

# 5. Simulate disaster - stop database
make stop

# 6. Restore from backup (replace with your backup name)
make restore BACKUP_DIR=backups/cluster_backup_20250706_152000
# Shows extraction progress:
# Extracted 1000/3917 files...
# Extracted 2000/3917 files...
# Restored size: 10.2GB
# ✓ Restore completed

# 7. Verify restore worked
make explore
# Generates reports showing all tables and data

# 8. Test with example app
cd ../example-app
make run
```

## Advanced Usage

### Manual Backup with Custom Options

```bash
docker run --rm \
    --network host \
    -e PGHOST=sych.local \
    -e PGPORT=8094 \
    -e PGUSER=jettison \
    -e PGPASSWORD=aMvzpGPgNVtH53S \
    -v $(PWD)/backups:/app/backups \
    timescaledb-save-restore \
    python save.py --output /app/backups --compress 9 --no-progress
```

### Backup Script Options

- `--compress N` - Compression level 0-9 (default: 6)
- `--format FORMAT` - "tar" or "plain" (default: tar)
- `--no-progress` - Disable progress reporting
- `--checkpoint MODE` - "fast" or "spread" (default: fast)

## Best Practices

1. **Test Restores Regularly** - Don't wait for a disaster to test
2. **Monitor Backup Sizes** - Sudden size changes may indicate issues
3. **Keep Multiple Backups** - At least 3 days of backups recommended
4. **Document Backup Times** - Know how long backup/restore takes
5. **Automate Backups** - Use cron for regular backups:
   ```bash
   0 2 * * * cd /path/to/db && make backup
   ```

## Performance Considerations

- **Backup Speed**: ~100-200 MB/s depending on disk and compression
- **Restore Speed**: ~150-250 MB/s for extraction
- **10GB Database**: Expect ~2-3 minutes for backup, ~1-2 minutes for restore
- **Space Needed**: 2x database size during restore (old + new data)

## Security Notes

- Backups contain **all database data** unencrypted
- Store backups securely with appropriate permissions
- Consider encrypting backup files for long-term storage
- Never commit backups to git (already in .gitignore)

## Troubleshooting Guide

### Problem: "REPLICATION permission denied"
```sql
-- Connect as superuser and run:
ALTER USER jettison REPLICATION;
```

### Problem: "No space left on device"
```bash
# Check available space
df -h .

# Clean old backups
rm -rf backups/cluster_backup_2025*
```

### Problem: Different PostgreSQL versions
Backups can only be restored to the same major version. Check with:
```bash
docker exec timescaledb-local postgres --version
```

### Problem: Restore seems stuck
Large databases take time. Check progress in Docker logs:
```bash
docker logs timescaledb-save-restore --follow
```

## Technical Architecture

- All operations run in Docker containers
- Uses official TimescaleDB images
- Network mode: host (simplifies connectivity)
- Data persisted in `mnt/db/postgres/`
- Backups stored in `backups/`
- Scripts written in Python for clarity