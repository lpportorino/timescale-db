.PHONY: help start stop status check-running explore backup restore list-backups clean build-images check-explorer-image check-save-restore-image

# No colors for terminal compatibility

# Default target - show help
help:
	@echo "=== TimescaleDB Database Management ==="
	@echo ""
	@echo "Database Commands:"
	@echo "  make start         - Start the TimescaleDB container"
	@echo "  make stop          - Stop the TimescaleDB container"
	@echo "  make status        - Check if database is running"
	@echo ""
	@echo "Tools:"
	@echo "  make explore       - Generate database documentation"
	@echo "  make backup        - Create a new backup"
	@echo "  make restore       - Restore from latest backup"
	@echo "  make list-backups  - List available backups"
	@echo ""
	@echo "Maintenance:"
	@echo "  make build-images  - Build all Docker images"
	@echo "  make clean         - Remove all data and backups (CAUTION!)"
	@echo ""
	@echo "Database connection info:"
	@echo "  Host: sych.local (or localhost)"
	@echo "  Port: 8094"
	@echo "  User: jettison"
	@echo "  Pass: aMvzpGPgNVtH53S"

# Check if database is running
check-running:
	@docker ps | grep -q timescaledb-local && echo "✓ Database is running" || (echo "✗ Database is not running" && echo "  Run 'make start' to start it" && exit 1)

# Start the database
start:
	@echo "Starting TimescaleDB..."
	@mkdir -p mnt/db/postgres config/postgres
	@docker run -d \
		--name timescaledb-local \
		--network host \
		-e POSTGRES_USER=jettison \
		-e POSTGRES_PASSWORD=aMvzpGPgNVtH53S \
		-e POSTGRES_DB=jettison \
		-v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
		-v $(PWD)/config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro \
		-v $(PWD)/config/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro \
		timescale/timescaledb-ha:pg17.2-ts2.18.0-all \
		-c 'config_file=/etc/postgresql/postgresql.conf' \
		&& echo "✓ Database started successfully" \
		|| echo "✗ Failed to start database"

# Start with restored data (skip initialization)
start-restored:
	@echo "Starting TimescaleDB with restored data..."
	@docker run -d \
		--name timescaledb-local \
		--network host \
		-e POSTGRES_PASSWORD=aMvzpGPgNVtH53S \
		-e PGDATA=/var/lib/postgresql/data \
		-v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
		timescale/timescaledb:latest-pg17 \
		-c 'port=8094' \
		&& echo "✓ Database started successfully" \
		|| echo "✗ Failed to start database"

# Stop the database
stop:
	@echo "Stopping TimescaleDB..."
	@docker stop timescaledb-local && docker rm timescaledb-local \
		&& echo "✓ Database stopped" \
		|| echo "Database was not running"

# Check database status
status:
	@docker ps | grep -q timescaledb-local \
		&& echo "✓ Database is running" \
		&& docker ps --filter name=timescaledb-local --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
		|| echo "✗ Database is not running"

# Check if explorer image exists
check-explorer-image:
	@docker images | grep -q timescaledb-explorer || (echo "Building explorer image..." && cd explore && docker build -t timescaledb-explorer .)

# Check if save-restore image exists
check-save-restore-image:
	@docker images | grep -q timescaledb-save-restore || (echo "Building save-restore image..." && cd save-restore && docker build -t timescaledb-save-restore .)

# Build all images
build-images:
	@echo "Building all Docker images..."
	@cd explore && docker build -t timescaledb-explorer .
	@cd save-restore && docker build -t timescaledb-save-restore .
	@echo "✓ All images built"

# Run database explorer
explore: check-running check-explorer-image
	@echo "Running database explorer..."
	@mkdir -p reports
	@docker run --rm \
		--network host \
		-v $(PWD)/reports:/output \
		timescaledb-explorer \
		--host $${PGHOST:-sych.local} \
		--port $${PGPORT:-8094} \
		--user $${PGUSER:-jettison} \
		--dbname $${PGDATABASE:-jettison} \
		--password $${PGPASSWORD:-aMvzpGPgNVtH53S} \
		--output /output/timescaledb_schema.md \
		--html
	@echo "✓ Reports generated in reports/"
	@ls -la reports/

# Create a backup
backup: check-running check-save-restore-image
	@echo "Creating database backup..."
	@docker run --rm \
		--network host \
		-e PGHOST=$${PGHOST:-sych.local} \
		-e PGPORT=$${PGPORT:-8094} \
		-e PGUSER=$${PGUSER:-jettison} \
		-e PGPASSWORD=$${PGPASSWORD:-aMvzpGPgNVtH53S} \
		-v $(PWD)/backups:/app/backups \
		timescaledb-save-restore save --backup-dir /app/backups --no-progress
	@echo "✓ Backup completed"

# Restore from backup - accepts BACKUP_DIR parameter
restore:
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "Available backups:"; \
		ls -la backups/; \
		echo ""; \
		echo "Usage: make restore BACKUP_DIR=backups/cluster_backup_YYYYMMDD_HHMMSS"; \
		exit 1; \
	fi
	@echo "WARNING: This will restore the database from backup."
	@echo "Backup: $(BACKUP_DIR)"
	@echo "Current data will be replaced. Continue? [y/N]"
	@read ans && [ $${ans:-N} = y ]
	@echo "Stopping database..."
	@docker stop timescaledb-local 2>/dev/null || true
	@docker rm -f timescaledb-local 2>/dev/null || true
	@echo "Waiting for container cleanup..."
	@sleep 2
	@echo "Clearing data directory..."
	@sudo rm -rf mnt/db/postgres/* 2>/dev/null || true
	@echo "Running restore..."
	@docker run --rm \
		-v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
		-v $(PWD)/$(BACKUP_DIR):/backup \
		-v $(PWD)/save-restore:/app \
		timescaledb-save-restore restore --backup /backup --force
	@echo "Running pg_resetwal to ensure clean startup..."
	@docker run --rm \
		-v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
		-e PGDATA=/var/lib/postgresql/data \
		-u 999:999 \
		timescale/timescaledb:latest-pg17 \
		pg_resetwal -f /var/lib/postgresql/data 2>/dev/null || true
	@echo "Starting database with restored data..."
	@make start-restored
	@echo "✓ Restore completed"

# List available backups
list-backups:
	@echo "Available backups:"
	@ls -la backups/ 2>/dev/null || echo "No backups found"

# Clean everything (DANGEROUS!)
clean:
	@echo "WARNING: This will delete ALL data and backups!"
	@echo "Are you absolutely sure? Type 'yes' to confirm:"
	@read ans && [ $${ans} = yes ]
	@make stop || true
	@rm -rf mnt/db/* backups/*
	@echo "✓ All data cleaned"