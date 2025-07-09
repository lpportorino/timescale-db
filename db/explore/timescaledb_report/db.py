"""
Database connection and basic query utilities.
"""

import psycopg2
import psycopg2.extras
import sys
import logging
from timescaledb_report.strings import get_string

logger = logging.getLogger(__name__)

def connect_to_db(db_params):
    """Establish connection to the TimescaleDB database

    Args:
        db_params (dict): Database connection parameters

    Returns:
        connection: PostgreSQL database connection

    Raises:
        SystemExit: If connection fails
    """
    try:
        conn = psycopg2.connect(**db_params)
        return conn
    except Exception as e:
        logger.error(get_string("log_messages.error_connecting",
                               "Error connecting to the database: {error}",
                               error=e))
        sys.exit(1)

def safe_query(db_params, query, params=None):
    """Safely execute a query that might fail if tables/views don't exist

    Args:
        db_params (dict): Database connection parameters
        query (str): SQL query to execute
        params (tuple, optional): Parameters for the query

    Returns:
        list: Query results as a list of dictionaries
    """
    # Create a new connection for each query to avoid transaction issues
    new_conn = None
    try:
        new_conn = psycopg2.connect(**db_params)
        with new_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            if params is None:
                params = ()
            # Handle edge cases - ensure params is a tuple or list
            if not isinstance(params, (tuple, list)):
                params = (params,)
            # If we have an empty string, make it None
            params = tuple(p if p != '' else None for p in params)

            logger.debug(f"Executing query: {query}")
            logger.debug(f"With parameters: {params}")

            cur.execute(query, params)
            result = cur.fetchall()
        return result
    except psycopg2.Error as e:
        if "relation" in str(e) and "does not exist" in str(e):
            return []
        else:
            logger.warning(get_string("log_messages.query_error",
                                      "Query error: {error}",
                                      error=e))
            return []
    except Exception as e:
        logger.warning(get_string("log_messages.unexpected_error",
                                 "Unexpected error during query: {error}",
                                 error=e))
        logger.debug(f"Failed query: {query[:200]}...")
        logger.debug(f"Error type: {type(e).__name__}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return []
    finally:
        if new_conn:
            try:
                new_conn.close()
            except Exception:
                pass

def check_if_extension_exists(db_params, extension_name):
    """Check if a specific PostgreSQL extension exists

    Args:
        db_params (dict): Database connection parameters
        extension_name (str): Name of the extension to check

    Returns:
        bool: True if the extension exists, False otherwise
    """
    # Use a separate connection to avoid transaction issues
    new_conn = None
    try:
        new_conn = psycopg2.connect(**db_params)
        with new_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_extension WHERE extname = %s;", (extension_name,))
            result = cur.fetchone()
        return result is not None
    except psycopg2.Error as e:
        logger.warning(get_string("log_messages.error_extension",
                                 "Error checking extension: {error}",
                                 error=e))
        return False
    finally:
        if new_conn:
            try:
                new_conn.close()
            except Exception:
                pass

def check_if_schema_exists(db_params, schema_name):
    """Check if a specific schema exists

    Args:
        db_params (dict): Database connection parameters
        schema_name (str): Name of the schema to check

    Returns:
        bool: True if the schema exists, False otherwise
    """
    # Use a separate connection to avoid transaction issues
    new_conn = None
    try:
        new_conn = psycopg2.connect(**db_params)
        with new_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s;", (schema_name,))
            result = cur.fetchone()
        return result is not None
    except psycopg2.Error as e:
        logger.warning(get_string("log_messages.error_schema",
                                 "Error checking schema: {error}",
                                 error=e))
        return False
    finally:
        if new_conn:
            try:
                new_conn.close()
            except Exception:
                pass

def get_database_size_info(db_params):
    """Get database size information
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        dict: Database size information
    """
    query = """
    SELECT 
        pg_database.datname,
        pg_size_pretty(pg_database_size(pg_database.datname)) AS total_size,
        pg_database_size(pg_database.datname) as size_bytes
    FROM pg_database
    WHERE datname = current_database()
    """
    
    try:
        result = safe_query(db_params, query)
        if result:
            return {
                'database': result[0]['datname'],
                'total_size': result[0]['total_size'],
                'size_bytes': result[0]['size_bytes']
            }
        return None
    except Exception as e:
        logger.error(f"Error getting database size: {e}")
        return None

def get_timescaledb_version(db_params):
    """Get the TimescaleDB version

    Args:
        db_params (dict): Database connection parameters

    Returns:
        str: TimescaleDB version or None if not installed
    """
    if not check_if_extension_exists(db_params, 'timescaledb'):
        return None

    # Use a separate connection to avoid transaction issues
    new_conn = None
    try:
        new_conn = psycopg2.connect(**db_params)
        with new_conn.cursor() as cur:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';")
            result = cur.fetchone()
        return result[0] if result else None
    except psycopg2.Error as e:
        logger.warning(get_string("log_messages.error_version",
                                 "Error getting TimescaleDB version: {error}",
                                 error=e))
        return None
    finally:
        if new_conn:
            try:
                new_conn.close()
            except Exception:
                pass
