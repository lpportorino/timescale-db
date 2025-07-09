"""
TimescaleDB Report Generator

A Python package to analyze TimescaleDB databases and generate
simplified schema-focused reports in Markdown format.
"""

from timescaledb_report.db import connect_to_db
from timescaledb_report.report import generate_markdown
from timescaledb_report.strings import get_string, load_config, get_config

__version__ = "1.2.0"
