.PHONY: help build run shell check-db

# No colors for terminal compatibility

# Default target
help:
	@echo "=== TimescaleDB Example App ==="
	@echo ""
	@echo "Available commands:"
	@echo "  make run      - Run the example application"
	@echo "  make build    - Build the Docker image"
	@echo "  make shell    - Open an interactive shell"
	@echo ""
	@echo "This is a template for building TimescaleDB apps"

# Check if database is running
check-db:
	@docker ps | grep -q timescaledb-local && echo "✓ Database is running" || (echo "✗ Database is not running" && echo "  Run 'cd ../db && make start' to start it" && exit 1)

# Build Docker image
build:
	@echo "Building example app image..."
	@docker build -t timescaledb-example-app .
	@echo "✓ Build complete"

# Run the application
run: build check-db
	@echo "Running example application..."
	@docker run --rm \
		--network host \
		-e PGHOST=$${PGHOST:-sych.local} \
		-e PGPORT=$${PGPORT:-8094} \
		-e PGUSER=$${PGUSER:-jettison} \
		-e PGPASSWORD=$${PGPASSWORD:-aMvzpGPgNVtH53S} \
		-e PGDATABASE=$${PGDATABASE:-jettison} \
		timescaledb-example-app

# Interactive shell
shell: build check-db
	@docker run --rm -it \
		--network host \
		-e PGHOST=$${PGHOST:-sych.local} \
		-e PGPORT=$${PGPORT:-8094} \
		-e PGUSER=$${PGUSER:-jettison} \
		-e PGPASSWORD=$${PGPASSWORD:-aMvzpGPgNVtH53S} \
		-e PGDATABASE=$${PGDATABASE:-jettison} \
		timescaledb-example-app bash