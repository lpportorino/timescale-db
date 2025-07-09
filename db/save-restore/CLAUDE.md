# CLAUDE.md - Save/Restore Tools

## Overview

Physical backup and restore tools using PostgreSQL's `pg_basebackup`. Chosen over logical backups (`pg_dump`) for reliability with active TimescaleDB clusters.

## Design Decisions

### Why pg_basebackup?

1. **No lock conflicts** - Avoids issues with autovacuum and continuous aggregates
2. **Complete backup** - Includes all databases, users, and settings
3. **Faster** - Physical copy vs logical export/import
4. **Consistent** - Point-in-time recovery capability

### Architecture Choices

1. **Tar format default** - Compression saves space (~10:1 ratio)
2. **Streaming WAL** - Ensures backup consistency
3. **Progress reporting** - User feedback for long operations
4. **Docker-based restore** - Consistent environment, no systemctl needed

## Implementation Details

### save.py

**Key Methods:**
- `test_connection()` - Verifies replication permission
- `estimate_size()` - Helps user plan disk space
- `create_backup()` - Runs pg_basebackup subprocess
- `verify_backup()` - Checks backup completeness

**Connection Flow:**
```python
psycopg2 connection → Check REPLICATION → pg_basebackup → Verify files
```

**Subprocess Management:**
```python
cmd = [
    'pg_basebackup',
    f'-h{self.host}',
    f'-p{self.port}',
    f'-U{self.user}',
    '-D', backup_path,
    '-Ft',  # Tar format
    f'-z{self.compress}',  # Compression
    '-Xs',  # Stream WAL
    '-P'    # Progress
]
```

### restore_docker.py

**Key Methods:**
- `check_prerequisites()` - Verify backup exists and format
- `clear_data_directory()` - Remove existing data
- `extract_tar_backup()` - Extract with progress reporting
- `set_permissions()` - Set postgres:postgres ownership
- `remove recovery files` - Clean backup_label and tablespace_map

**Restore Flow:**
```
Clear data → Extract backup → Set permissions → Remove recovery files → Report size
```

**Critical Implementation Details:**
- Shows "Extracted X/Y files..." progress
- Removes backup_label automatically (prevents startup issues)
- Removes tablespace_map if present
- Reports final size: "Restored size: 10.2GB"
- Uses UID/GID 999 for postgres user in container

## Critical Restore Discoveries

### WAL Recovery Issues

After restore, PostgreSQL may fail with "could not locate a valid checkpoint record". This happens because:
1. pg_basebackup includes backup_label file
2. This file tells PostgreSQL to look for WAL files
3. If WAL is inconsistent, startup fails

**Solution:** Use pg_resetwal after removing backup_label:
```bash
docker run --rm -u postgres -v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
    timescale/timescaledb:latest-pg17 pg_resetwal -f /var/lib/postgresql/data
```

### Container Initialization Conflicts

TimescaleDB images with initialization scripts can conflict with restored data:
1. Container sees existing PGDATA directory
2. But may still run initialization
3. This can overwrite or ignore restored data

**Solution:** Use `make start-restored` which skips initialization.

### File Ownership in Docker

PostgreSQL in Docker runs as UID/GID 999:
- Host sees files owned by user 999
- Container sees them as postgres:postgres
- This is normal and expected

## Common Issues and Solutions

### Replication Permission

**Issue:** User lacks REPLICATION role
**Solution:** 
```sql
ALTER USER jettison REPLICATION;
```

### Disk Space

**Issue:** Insufficient space for backup
**Solution:** 
- Use higher compression (`-z9`)
- Clean old backups
- Use external storage

### Version Mismatch

**Issue:** Backup from different PostgreSQL version
**Solution:** 
- Use same major version
- Or use pg_upgrade after restore

## Performance Tuning

### Backup Performance

1. **Compression Level** - Balance speed vs size
   - 0: No compression (fastest)
   - 6: Default (balanced)
   - 9: Maximum (slowest)

2. **Checkpoint Mode**
   - "fast": Immediate checkpoint
   - "spread": Less I/O impact

3. **Network Bandwidth**
   - Use `--max-rate` to limit

### Restore Performance

1. **Extraction** - CPU bound for compressed backups
2. **Permission Setting** - I/O bound for large clusters
3. **Service Management** - May need custom timeout

## Integration Patterns

### With Docker

```dockerfile
# Needs pg_basebackup client
RUN apt-get install postgresql-client-15

# For restore - needs privileged mode
docker run --privileged ...
```

### With Scheduling

```bash
# Cron example
0 2 * * * cd /path/to/save-restore && make save
```

### With Monitoring

Check exit codes:
- 0: Success
- 1: Connection/permission error
- 2: Disk space error
- 3: Backup verification failed

## Security Considerations

1. **Password Handling** - Currently in environment
   - TODO: Support .pgpass file
   - TODO: Support password prompt

2. **Backup Storage** - Unencrypted by default
   - Consider encrypting at rest
   - Limit file permissions

3. **Network Security** - Uses PostgreSQL SSL if configured

## Testing Strategies

### Unit Testing
```python
# Mock subprocess calls
@patch('subprocess.Popen')
def test_backup_command(mock_popen):
    # Verify command construction
```

### Integration Testing
1. Create test database
2. Add test data
3. Run backup
4. Restore to different location
5. Verify data integrity

## Future Improvements

1. **Incremental Backups** - Using WAL archiving
2. **Cloud Storage** - S3/GCS integration
3. **Parallel Compression** - Multiple threads
4. **Backup Catalog** - Track backup metadata
5. **Automated Testing** - CI/CD integration