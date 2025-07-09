"""
Descriptions for TimescaleDB database components.

This file contains functions to retrieve descriptive information about tables,
columns, indices, and other database components. It loads descriptions from the
TOML configuration file.
"""

import logging
from timescaledb_report.strings import get_string

logger = logging.getLogger(__name__)

def get_table_purpose(table_name):
    """Get the purpose description for a table

    Args:
        table_name (str): Name of the table

    Returns:
        str: Purpose description for the table
    """
    # Check for redis_logs specifically
    if table_name == "redis_logs":
        return "Log entries streamed from Redis for applications and services"

    # Try to get specific table purpose, fall back to default
    purpose = get_string(f"table_purposes.{table_name}",
                         default=get_string("table_purposes.default", "Data storage"))
    return purpose

def get_column_purpose(table_name, column_name, data_type):
    """
    Determine the purpose of a column based on patterns and specific overrides

    Args:
        table_name (str): Name of the table containing the column
        column_name (str): Name of the column
        data_type (str): Data type of the column

    Returns:
        str: Description of the column's purpose
    """
    # Handle redis_logs columns specifically
    if table_name == "redis_logs":
        if column_name == "time":
            return "Timestamp when the log entry was received from Redis"
        elif column_name == "data":
            return "Complete log entry data in JSON format containing the full message context"
        elif column_name == "severity":
            return "Log severity level (info, error, status, crash)"
        elif column_name == "stream_key":
            return "Redis stream identifier, shows which application stream the log came from"
        elif column_name == "message":
            return "Actual log message content extracted from the data JSON"

    # Check for specific table-column override first
    specific_purpose = get_string(f"specific_column_purposes.{table_name}.{column_name}")
    if specific_purpose:
        return specific_purpose

    # Check for exact column name match
    exact_purpose = get_string(f"column_purposes.exact.{column_name}")
    if exact_purpose:
        return exact_purpose

    # Check for data type matches
    data_type_lower = data_type.lower()
    for type_pattern in ["jsonb", "json", "uuid", "boolean"]:
        if type_pattern in data_type_lower:
            type_purpose = get_string(f"column_purposes.type.{type_pattern}")
            if type_purpose:
                return type_purpose

    # Check for pattern matches
    column_name_lower = column_name.lower()
    for pattern in ["id", "json", "timestamp", "created_at", "updated_at", "is_", "has_"]:
        if pattern in column_name_lower:
            pattern_purpose = get_string(f"column_purposes.pattern.{pattern}")
            if pattern_purpose:
                return pattern_purpose

    # Default empty if no match found
    return ""

def get_index_purpose(index_name, columns, is_primary, is_unique, table_name):
    """
    Determine the purpose of an index based on patterns

    Args:
        index_name (str): Name of the index
        columns (str): Comma-separated list of columns in the index
        is_primary (bool): Whether this is a primary key
        is_unique (bool): Whether this is a unique index
        table_name (str): Name of the table this index belongs to

    Returns:
        str: Description of the index's purpose
    """
    index_name_lower = index_name.lower()
    columns_lower = columns.lower()

    # Handle redis_logs indexes specifically
    if table_name == "redis_logs":
        if "time_severity" in index_name_lower:
            return "Optimizes queries filtering by time and severity level"
        elif "stream_lookup" in index_name_lower:
            return "Enables efficient filtering by stream source and time"
        elif "errors" in index_name_lower:
            return "Optimizes queries for error-level messages"
        elif "message_trgm" in index_name_lower:
            return "Provides full-text search capabilities within log messages"
        elif "time_idx" in index_name_lower:
            return "Primary time-series index for TimescaleDB chunking and partitioning"

    # Check primary and unique first
    if is_primary:
        return get_string("index_purposes.special.primary_key", "Primary key lookup")
    if is_unique:
        return get_string("index_purposes.special.unique", "Enforce uniqueness/lookup by unique value")

    # Check index name patterns
    for pattern in ["gin", "time_idx", "pkey"]:
        if pattern in index_name_lower:
            purpose = get_string(f"index_purposes.name.{pattern}")
            if purpose:
                return purpose

    # Check for multi-column patterns
    if len(columns_lower.split(',')) > 1:
        for pattern in ["time_", "_time", "service_category", "error_"]:
            if pattern in columns_lower or pattern in index_name_lower:
                purpose = get_string(f"index_purposes.multi.{pattern}")
                if purpose:
                    return purpose
        return get_string("index_purposes.special.multi_column", "Multi-column filtering/grouping")

    # Check column patterns
    for pattern in ["time", "severity", "level", "status"]:
        if pattern in columns_lower:
            purpose = get_string(f"index_purposes.columns.{pattern}")
            if purpose:
                return purpose

    # Table-specific purposes
    if table_name.endswith('_logs') and 'severity' in columns_lower:
        return get_string("index_purposes.special.logs_severity", "Filter logs by severity")
    if table_name.endswith('_alerts') and ('level' in columns_lower or 'severity' in columns_lower):
        return get_string("index_purposes.special.alerts_level", "Filter alerts by importance")

    # Default
    return get_string("index_purposes.special.default", "General filtering/lookup")
