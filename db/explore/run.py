#!/usr/bin/env python3

import argparse
import sys
import os
import logging
from pathlib import Path
import yaml
import json
import traceback
from timescaledb_report import connect_to_db, generate_markdown
from timescaledb_report.strings import get_string
from timescaledb_report.html import generate_html_report

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('run')

# Default database connection parameters
DEFAULT_DB_PARAMS = {
    'dbname': 'jettison',
    'user': 'jettison',
    'password': 'aMvzpGPgNVtH53S',
    'host': '172.23.90.145',
    'port': 8094
}

def parse_args():
    parser = argparse.ArgumentParser(
        description=get_string("cli.description", "Generate a TimescaleDB database schema report")
    )

    parser.add_argument('-o', '--output',
                        help=get_string("cli.output_help", "Output file name (default: timescaledb_schema.md)"),
                        default='timescaledb_schema.md')

    parser.add_argument('--html', action='store_true',
                        help=get_string("cli.html_help", "Generate HTML report in addition to Markdown"))

    parser.add_argument('--html-only', action='store_true',
                        help=get_string("cli.html_only_help", "Generate only HTML report, no Markdown file"))

    parser.add_argument('-c', '--config',
                        help=get_string("cli.config_help", "Path to config file (YAML or JSON)"))

    parser.add_argument('-H', '--host',
                        help=get_string("cli.host_help", "Database host (default: {host})",
                                        host=DEFAULT_DB_PARAMS["host"]))

    parser.add_argument('-p', '--port', type=int,
                        help=get_string("cli.port_help", "Database port (default: {port})",
                                        port=DEFAULT_DB_PARAMS["port"]))

    parser.add_argument('-U', '--user',
                        help=get_string("cli.user_help", "Database user (default: {user})",
                                        user=DEFAULT_DB_PARAMS["user"]))

    parser.add_argument('-d', '--dbname',
                        help=get_string("cli.dbname_help", "Database name (default: {dbname})",
                                        dbname=DEFAULT_DB_PARAMS["dbname"]))

    parser.add_argument('-P', '--password',
                        help=get_string("cli.password_help",
                                        "Database password (not recommended, use config file instead)"))

    parser.add_argument('-v', '--verbose', action='store_true',
                        help=get_string("cli.verbose_help", "Enable verbose logging"))

    return parser.parse_args()

def load_config(config_path):
    """Load configuration from a YAML or JSON file"""
    if not config_path:
        return {}

    path = Path(config_path)
    if not path.exists():
        logger.error(get_string("cli.config_not_found", "Config file not found: {path}", path=config_path))
        return {}

    try:
        if path.suffix in ['.yaml', '.yml']:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        elif path.suffix == '.json':
            with open(path, 'r') as f:
                return json.load(f)
        else:
            logger.error(get_string("cli.unsupported_format",
                                    "Unsupported config file format: {suffix}",
                                    suffix=path.suffix))
            return {}
    except Exception as e:
        logger.error(get_string("cli.error_loading_config", "Error loading config: {error}", error=e))
        return {}

def merge_db_params(args, config):
    """Merge DB parameters from config file and command-line args"""
    db_params = DEFAULT_DB_PARAMS.copy()

    # Update from config if it exists
    if config and 'database' in config:
        db_params.update(config['database'])

    # Command-line args take precedence
    if args.host:
        db_params['host'] = args.host
    if args.port:
        db_params['port'] = args.port
    if args.user:
        db_params['user'] = args.user
    if args.dbname:
        db_params['dbname'] = args.dbname
    if args.password:
        db_params['password'] = args.password

    # Check for password in environment variable
    if 'PGPASSWORD' in os.environ and not args.password:
        db_params['password'] = os.environ['PGPASSWORD']

    return db_params

def main():
    args = parse_args()

    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load config if specified
    config = load_config(args.config)

    # Merge DB parameters
    db_params = merge_db_params(args, config)

    # Output file
    output_file = args.output

    try:
        # Test connection first
        test_conn = connect_to_db(db_params)
        test_conn.close()
        logger.info(get_string("cli.connection_success",
                              "Successfully connected to database {dbname} at {host}:{port}",
                              dbname=db_params['dbname'],
                              host=db_params['host'],
                              port=db_params['port']))

        # Only generate Markdown if not html-only mode
        if not args.html_only:
            # Generate the report
            result = generate_markdown(db_params, output_file)
            if result:
                logger.info(get_string("cli.report_success",
                                      "Schema report generated successfully: {file}",
                                      file=output_file))
            else:
                logger.error(get_string("cli.report_failure", "Failed to generate schema report"))
                sys.exit(1)

        # Generate HTML if requested
        if args.html or args.html_only:
            if args.html_only:
                # Generate a temporary markdown file
                temp_md = f"temp_{db_params['dbname']}.md"
                result = generate_markdown(db_params, temp_md)
                if result:
                    html_file = os.path.splitext(output_file)[0] + '.html'
                    generate_html_report(temp_md, html_file)
                    # Remove temporary file
                    os.remove(temp_md)
                    logger.info(get_string("cli.html_success",
                                          "HTML schema report generated successfully: {file}",
                                          file=html_file))
                else:
                    logger.error(get_string("cli.temp_failure",
                                           "Failed to generate temporary Markdown for HTML report"))
                    sys.exit(1)
            else:
                html_file = os.path.splitext(output_file)[0] + '.html'
                generate_html_report(output_file, html_file)
                logger.info(get_string("cli.html_success",
                                       "HTML schema report generated successfully: {file}",
                                       file=html_file))

    except Exception as e:
        logger.error(get_string("log_messages.error_report", "Error generating report: {error}", error=e))
        if args.verbose:
            logger.error(traceback.format_exc())
        else:
            logger.info(get_string("cli.verbose_hint",
                                  "Run with --verbose for more information on this error"))
        sys.exit(1)

if __name__ == "__main__":
    main()
