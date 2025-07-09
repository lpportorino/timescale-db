"""
Functions for working with TimescaleDB hypertables.
"""

import logging
from timescaledb_report.db import check_if_extension_exists, check_if_schema_exists, safe_query

logger = logging.getLogger(__name__)

def is_hypertable(db_params, table_name):
    """Check if the given table is a TimescaleDB hypertable

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to check

    Returns:
        bool: True if table is a hypertable, False otherwise
    """
    # First, check if TimescaleDB is installed
    if not check_if_extension_exists(db_params, 'timescaledb'):
        return False

    # Check if timescaledb_information schema exists (for newer versions)
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        result = safe_query(
            db_params,
            "SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = %s;",
            (table_name,)
        )
        if result:
            return True

    # Fallback for older TimescaleDB versions
    result = safe_query(
        db_params,
        """
        SELECT 1 FROM _timescaledb_catalog.hypertable h
        JOIN _timescaledb_catalog.hypertable_schema s ON h.id = s.hypertable_id
        WHERE s.schema_name = 'public' AND h.table_name = %s;
        """,
        (table_name,)
    )

    return len(result) > 0

def get_hypertable_info(db_params, table_name):
    """Get hypertable information for a given table

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get hypertable info for

    Returns:
        dict: Hypertable information or None if not a hypertable
    """
    if not is_hypertable(db_params, table_name):
        return None

    hypertable_info = {}

    # Try newer TimescaleDB version first (2.x+)
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        result = safe_query(
            db_params,
            """
            SELECT *
            FROM timescaledb_information.hypertables
            WHERE hypertable_name = %s;
            """,
            (table_name,)
        )
        if result:
            return dict(result[0])

        # Try to get time dimension info directly
        result = safe_query(
            db_params,
            """
            SELECT d.column_name, d.time_interval
            FROM timescaledb_information.dimensions d
            WHERE d.hypertable_name = %s
              AND d.dimension_number = 0;
            """,
            (table_name,)
        )
        if result:
            hypertable_info['time_column'] = result[0]['column_name']
            hypertable_info['chunk_time_interval'] = result[0]['time_interval']

    # If we didn't get what we need from the information schema, try the catalog
    if 'time_column' not in hypertable_info:
        # Get hypertable ID first
        result = safe_query(
            db_params,
            """
            SELECT h.id
            FROM _timescaledb_catalog.hypertable h
            WHERE h.schema_name = 'public' AND h.table_name = %s;
            """,
            (table_name,)
        )

        if result:
            hypertable_id = result[0]['id']

            # Get time dimension info
            result = safe_query(
                db_params,
                """
                SELECT d.column_name, d.interval_length
                FROM _timescaledb_catalog.dimension d
                WHERE d.hypertable_id = %s AND d.column_type = 'TIME';
                """,
                (hypertable_id,)
            )

            if result:
                hypertable_info['time_column'] = result[0]['column_name']
                hypertable_info['chunk_time_interval'] = result[0]['interval_length']

            # Check if compressed
            result = safe_query(
                db_params,
                """
                SELECT compressed_hypertable_id IS NOT NULL as is_compressed
                FROM _timescaledb_catalog.hypertable
                WHERE id = %s;
                """,
                (hypertable_id,)
            )

            if result:
                hypertable_info['is_compressed'] = result[0]['is_compressed']

    # If we still don't have the information, try another approach for older versions
    if 'time_column' not in hypertable_info:
        # For TimescaleDB 1.x versions
        result = safe_query(
            db_params,
            """
            SELECT c.column_name
            FROM pg_attribute a
            JOIN pg_class t ON a.attrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            JOIN _timescaledb_catalog.dimension d ON d.column_name = a.attname
            JOIN _timescaledb_catalog.hypertable h ON d.hypertable_id = h.id
            JOIN information_schema.columns c ON
                c.table_schema = n.nspname AND
                c.table_name = t.relname AND
                c.column_name = a.attname
            WHERE t.relname = %s
              AND n.nspname = 'public'
              AND d.column_type = 'TIME';
            """,
            (table_name,)
        )

        if result:
            hypertable_info['time_column'] = result[0]['column_name']

    # If we got information from any source, return it
    if hypertable_info:
        return hypertable_info

    # Last attempt - just return basic info
    result = safe_query(
        db_params,
        """
        SELECT h.table_name, h.schema_name
        FROM _timescaledb_catalog.hypertable h
        WHERE h.schema_name = 'public' AND h.table_name = %s
        """,
        (table_name,)
    )

    return dict(result[0]) if result else None

def get_chunk_stats(db_params, table_name):
    """Get statistics about chunks for a hypertable

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get chunk stats for

    Returns:
        dict: Chunk statistics including count, size, etc.
    """
    if not is_hypertable(db_params, table_name):
        return None

    # Check what columns are available in the chunks view
    chunk_columns = []
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        result = safe_query(
            db_params,
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'timescaledb_information'
              AND table_name = 'chunks';
            """
        )
        if result:
            chunk_columns = [row['column_name'] for row in result]

    # For TimescaleDB 2.x+ with known column structure
    if chunk_columns:
        # Different versions of TimescaleDB might have different column names
        size_column = None
        for col in ['total_bytes', 'table_bytes', 'table_size']:
            if col in chunk_columns:
                size_column = col
                break

        # Build a query based on available columns
        range_cols = []
        if 'range_start' in chunk_columns and 'range_end' in chunk_columns:
            range_cols = ['MIN(range_start) as oldest_chunk', 'MAX(range_end) as newest_chunk']
        elif 'chunk_range_start' in chunk_columns and 'chunk_range_end' in chunk_columns:
            range_cols = ['MIN(chunk_range_start) as oldest_chunk', 'MAX(chunk_range_end) as newest_chunk']
        elif 'range_start_integer' in chunk_columns and 'range_end_integer' in chunk_columns:
            range_cols = ['MIN(range_start_integer) as oldest_chunk', 'MAX(range_end_integer) as newest_chunk']

        size_col = []
        if size_column:
            size_col = [f'SUM({size_column}) as total_size']

        cols = ['COUNT(*) as chunk_count'] + size_col + range_cols

        query = f"""
        SELECT {', '.join(cols)}
        FROM timescaledb_information.chunks
        WHERE hypertable_name = %s;
        """

        result = safe_query(db_params, query, (table_name,))

        if result and result[0]['chunk_count'] > 0:
            return dict(result[0])

    # For older versions or if the previous query failed - get the basic chunk count
    result = safe_query(
        db_params,
        """
        SELECT
            COUNT(*) as chunk_count
        FROM _timescaledb_catalog.chunk c
        JOIN _timescaledb_catalog.hypertable h ON c.hypertable_id = h.id
        WHERE h.schema_name = 'public' AND h.table_name = %s;
        """,
        (table_name,)
    )

    # If chunk count available, try to get size info a safer way
    if result:
        chunk_stats = {"chunk_count": result[0]['chunk_count']}

        # Get hypertable ID
        hypertable_result = safe_query(
            db_params,
            """
            SELECT id
            FROM _timescaledb_catalog.hypertable
            WHERE schema_name = 'public' AND table_name = %s;
            """,
            (table_name,)
        )

        if hypertable_result and len(hypertable_result) > 0:
            try:
                hypertable_id = hypertable_result[0]['id']

                # Get aggregated size directly with planner statistics
                size_result = safe_query(
                    db_params,
                    """
                    SELECT
                        pg_size_pretty(SUM(pg_relation_size(c.table_name::regclass))) as pretty_size,
                        SUM(pg_relation_size(c.table_name::regclass)) as total_size
                    FROM _timescaledb_catalog.chunk c
                    WHERE c.hypertable_id = %s;
                    """,
                    (hypertable_id,)
                )

                if size_result and len(size_result) > 0:
                    if 'total_size' in size_result[0]:
                        chunk_stats['total_size'] = size_result[0]['total_size']
                    if 'pretty_size' in size_result[0]:
                        chunk_stats['pretty_size'] = size_result[0]['pretty_size']
            except (KeyError, IndexError, Exception) as e:
                logger.warning(f"Error getting chunk sizes for {table_name}: {e}")

        return chunk_stats

    return {"chunk_count": 0}
