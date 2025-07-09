"""
Functions for retrieving database schema information.
"""

import logging
import psycopg2
from timescaledb_report.strings import get_string
from timescaledb_report.db import safe_query

logger = logging.getLogger(__name__)

def get_all_tables(db_params):
    """Get a list of all tables in the public schema

    Args:
        db_params (dict): Database connection parameters

    Returns:
        list: List of table names
    """
    # Use a separate connection to avoid transaction issues
    new_conn = None
    try:
        new_conn = psycopg2.connect(**db_params)
        with new_conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            tables = cur.fetchall()
        return [table[0] for table in tables]
    except psycopg2.Error as e:
        logger.error(f"Error getting tables: {e}")
        return []
    finally:
        if new_conn:
            new_conn.close()

def get_table_schema(db_params, table_name):
    """Get the schema (columns and data types) for a given table

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get schema for

    Returns:
        list: List of column dictionaries with name, type, nullable, and default
    """
    # Use a separate connection to avoid transaction issues
    new_conn = None
    try:
        new_conn = psycopg2.connect(**db_params)
        with new_conn.cursor() as cur:
            cur.execute("""
                SELECT
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            columns = cur.fetchall()

        schema_info = []
        for col in columns:
            col_name, data_type, max_length, nullable, default = col
            if max_length:
                data_type = f"{data_type}({max_length})"
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            default_str = f"{default}" if default else ""

            schema_info.append({
                "name": col_name,
                "type": data_type,
                "nullable": nullable_str,
                "default": default_str
            })

        return schema_info
    except psycopg2.Error as e:
        logger.warning(get_string("log_messages.error_schema_table",
                                 "Error getting table schema for {table}: {error}",
                                 table=table_name, error=e))
        return []
    finally:
        if new_conn:
            new_conn.close()

def get_indexes(db_params, table_name):
    """Get index information for a given table

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get indexes for

    Returns:
        dict: Dictionary of indexes with columns and properties
    """
    result = safe_query(
        db_params,
        """
        SELECT
            i.relname as index_name,
            a.attname as column_name,
            ix.indisunique as is_unique,
            ix.indisprimary as is_primary
        FROM
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_attribute a
        WHERE
            t.oid = ix.indrelid
            AND i.oid = ix.indexrelid
            AND a.attrelid = t.oid
            AND a.attnum = ANY(ix.indkey)
            AND t.relkind = 'r'
            AND t.relname = %s
        ORDER BY
            t.relname,
            i.relname,
            array_position(ix.indkey, a.attnum);
        """,
        (table_name,)
    )

    indexes = {}
    for r in result:
        idx_name = r['index_name']
        if idx_name not in indexes:
            indexes[idx_name] = {
                'columns': [],
                'is_unique': r['is_unique'],
                'is_primary': r['is_primary']
            }
        indexes[idx_name]['columns'].append(r['column_name'])

    return indexes
