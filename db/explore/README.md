# TimescaleDB Schema Explorer

A comprehensive database documentation tool that analyzes your TimescaleDB database and generates detailed reports in both Markdown and HTML formats.

## Features

- **Complete Schema Documentation** - Documents all tables with their purposes and relationships
- **TimescaleDB Aware** - Understands hypertables, continuous aggregates, and retention policies
- **Performance Analysis** - Identifies unused indexes and provides optimization suggestions
- **Executive Summary** - Health score with key metrics at a glance
- **Multiple Output Formats** - Both Markdown (for version control) and HTML (for browsing)
- **Flexible Configuration** - CLI arguments, config files, or environment variables

## Usage

### Via Docker (Recommended)

From the `db/` directory:

```bash
# Make sure database is running
make status

# Generate reports
make explore
```

Reports will be generated in `db/reports/`:
- `timescaledb_schema.md` - Markdown format
- `timescaledb_schema.html` - HTML format with navigation

### Direct Python Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default settings
python run.py

# Custom connection parameters
python run.py --host localhost --port 5432 --user myuser --dbname mydb

# Generate only HTML
python run.py --html-only --output schema.html

# Use config file
python run.py --config database.yaml

# Verbose mode for debugging
python run.py --verbose
```

## Configuration

### Environment Variables

```bash
export PGHOST=localhost
export PGPORT=5432
export PGUSER=myuser
export PGPASSWORD=mypassword
export PGDATABASE=mydb
```

### Config File (YAML)

```yaml
database:
  host: localhost
  port: 5432
  user: myuser
  password: mypassword
  dbname: mydb
```

### Config File (JSON)

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "user": "myuser",
    "password": "mypassword",
    "dbname": "mydb"
  }
}
```

## Output Examples

### Executive Summary

The tool provides a health score and key metrics:

```
Database Health Score: 85/100

Warnings:
- 23 unused indexes found
- 2 tables without primary keys

Key Metrics:
- Total Database Size: 1.2 GB
- Continuous Aggregates: 3
- Hypertables: 5
- Total Indexes: 45
```

### Table Documentation

Each table is documented with:
- Purpose description
- Schema details with column purposes
- Index information
- TimescaleDB-specific features
- Related continuous aggregates

### Performance Insights

- Identifies unused indexes
- Shows compression effectiveness
- Tracks chunk counts
- Monitors connection statistics

## Development

### Project Structure

```
explore/
├── run.py                          # CLI entry point
├── requirements.txt                # Python dependencies
├── setup.py                        # Package setup
├── timescaledb_report/            # Main package
│   ├── __init__.py
│   ├── db.py                      # Database connectivity
│   ├── schema.py                  # Schema extraction
│   ├── hypertable.py              # TimescaleDB features
│   ├── policies.py                # Policy analysis
│   ├── stats.py                   # Performance metrics
│   ├── descriptions.py            # Table/column descriptions
│   ├── report.py                  # Markdown generation
│   ├── html.py                    # HTML generation
│   └── strings.py                 # Internationalization
└── timescaledb_report_strings.toml # Localized strings
```

### Adding New Features

1. **New Metrics** - Add to `stats.py`
2. **New Descriptions** - Update `descriptions.py`
3. **New Report Sections** - Modify `report.py`
4. **New CLI Options** - Update `run.py`

## Docker Build

The Dockerfile installs all dependencies and sets up the environment:

```dockerfile
FROM python:3.11-slim

# Install PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

ENTRYPOINT ["python", "/app/run.py"]
```

## Troubleshooting

### Connection Issues

- Verify database is running: `cd ../db && make status`
- Check connection parameters match your setup
- Ensure network connectivity to database host

### Missing Dependencies

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install libpq-dev python3-dev

# Install Python packages
pip install -r requirements.txt
```

### Permission Errors

Generated reports may be owned by root when run via Docker. To fix:

```bash
sudo chown -R $USER:$USER reports/
```