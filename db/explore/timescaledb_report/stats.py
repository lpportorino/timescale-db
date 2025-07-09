"""
Enhanced database statistics collection for comprehensive reporting.
"""

import logging
from timescaledb_report.db import safe_query

logger = logging.getLogger(__name__)

def execute_query(db_params, query):
    """Execute a query and return results as list of tuples.
    
    Args:
        db_params (dict): Database connection parameters
        query (str): SQL query to execute
        
    Returns:
        list: Query results as list of tuples
    """
    result = safe_query(db_params, query)
    if result:
        # Convert DictRow results to tuples - handle different row types
        try:
            # Try to convert each row properly
            converted_results = []
            for row in result:
                if hasattr(row, 'values'):
                    # DictRow has values() method
                    converted_results.append(tuple(row.values()))
                elif hasattr(row, '__iter__'):
                    # Already a tuple or list
                    converted_results.append(tuple(row))
                else:
                    # Fallback - convert to list first
                    converted_results.append(tuple(list(row)))
            return converted_results
        except Exception as e:
            logger.error(f"Error converting query results: {e}")
            # Try a simpler conversion
            return [tuple(row) for row in result]
    return []

def get_database_health_score(db_params):
    """Calculate an overall database health score based on various metrics.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        dict: Health score and contributing factors
    """
    score = 100
    issues = []
    warnings = []
    
    try:
        # Check for unused indexes (deduct points for waste)
        unused_indexes = get_unused_indexes(db_params)
        if unused_indexes:
            deduction = min(len(unused_indexes) * 2, 20)
            score -= deduction
            warnings.append(f"{len(unused_indexes)} unused indexes found")
        
        # Check table bloat
        bloated_tables = get_bloated_tables(db_params)
        if bloated_tables:
            deduction = min(len(bloated_tables) * 5, 25)
            score -= deduction
            issues.append(f"{len(bloated_tables)} tables with significant bloat")
        
        # Check for tables without compression
        uncompressed = get_uncompressed_hypertables(db_params)
        if uncompressed:
            deduction = min(len(uncompressed) * 3, 15)
            score -= deduction
            warnings.append(f"{len(uncompressed)} hypertables without compression")
        
        # Check query performance
        slow_queries = get_slow_queries(db_params, limit=10)
        if slow_queries:
            avg_time = sum(q['mean_exec_time'] for q in slow_queries) / len(slow_queries)
            if avg_time > 1000:  # > 1 second
                score -= 10
                issues.append(f"Average slow query time: {avg_time:.1f}ms")
        
        return {
            'score': max(score, 0),
            'issues': issues,
            'warnings': warnings
        }
        
    except Exception as e:
        logger.error(f"Error calculating health score: {e}")
        return {
            'score': None,
            'issues': ['Unable to calculate health score'],
            'warnings': []
        }

def get_connection_statistics(db_params):
    """Get current database connection statistics.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Connection statistics by state
    """
    query = """
    SELECT 
        state,
        COUNT(*) as connection_count,
        MAX(EXTRACT(EPOCH FROM (now() - state_change))) as max_duration_seconds
    FROM pg_stat_activity
    WHERE pid != pg_backend_pid()
    GROUP BY state
    ORDER BY connection_count DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'state': row[0] or 'active',
            'count': row[1],
            'max_duration_seconds': row[2]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting connection statistics: {e}")
        return []

def get_slow_queries(db_params, limit=20):
    """Get slowest queries from pg_stat_statements.
    
    Args:
        db_params (dict): Database connection parameters
        limit (int): Number of queries to return
        
    Returns:
        list: Slow query information
    """
    query = f"""
    SELECT 
        LEFT(query, 100) as query_preview,
        calls,
        mean_exec_time,
        total_exec_time,
        min_exec_time,
        max_exec_time,
        stddev_exec_time
    FROM pg_stat_statements
    WHERE query NOT LIKE '%%pg_stat_statements%%'
    ORDER BY mean_exec_time DESC
    LIMIT {limit}
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'query': row[0],
            'calls': row[1],
            'mean_exec_time': row[2],
            'total_exec_time': row[3],
            'min_exec_time': row[4],
            'max_exec_time': row[5],
            'stddev_exec_time': row[6]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting slow queries: {e}")
        return []

def get_unused_indexes(db_params):
    """Get indexes that have never been used.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Unused index information
    """
    query = """
    SELECT 
        n.nspname as schemaname,
        t.relname as tablename,
        i.relname as indexname,
        pg_size_pretty(pg_relation_size(ui.indexrelid)) as index_size,
        pg_relation_size(ui.indexrelid) as size_bytes
    FROM pg_stat_user_indexes ui
    JOIN pg_index idx ON idx.indexrelid = ui.indexrelid
    JOIN pg_class i ON i.oid = ui.indexrelid
    JOIN pg_class t ON t.oid = ui.relid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE ui.idx_scan = 0
        AND n.nspname = 'public'
        AND i.relname NOT LIKE '%%_pkey'
    ORDER BY pg_relation_size(ui.indexrelid) DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'schema': row[0],
            'table': row[1],
            'index': row[2],
            'size': row[3],
            'size_bytes': row[4]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting unused indexes: {e}")
        return []

def get_index_usage_statistics(db_params):
    """Get detailed index usage statistics.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Index usage statistics
    """
    query = """
    SELECT 
        n.nspname as schemaname,
        t.relname as tablename,
        i.relname as indexname,
        ui.idx_scan,
        ui.idx_tup_read,
        ui.idx_tup_fetch,
        pg_size_pretty(pg_relation_size(ui.indexrelid)) as index_size
    FROM pg_stat_user_indexes ui
    JOIN pg_class i ON i.oid = ui.indexrelid
    JOIN pg_class t ON t.oid = ui.relid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
    ORDER BY ui.idx_scan DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'schema': row[0],
            'table': row[1],
            'index': row[2],
            'scans': row[3],
            'tuples_read': row[4],
            'tuples_fetched': row[5],
            'size': row[6]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting index usage statistics: {e}")
        return []

def get_table_access_patterns(db_params):
    """Get table access patterns showing sequential vs index scans.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Table access pattern information
    """
    query = """
    SELECT 
        n.nspname as schemaname,
        c.relname as tablename,
        t.seq_scan,
        t.seq_tup_read,
        t.idx_scan,
        t.idx_tup_fetch,
        t.n_tup_ins,
        t.n_tup_upd,
        t.n_tup_del,
        t.n_live_tup,
        t.n_dead_tup,
        CASE 
            WHEN t.seq_scan + t.idx_scan = 0 THEN 0
            ELSE ROUND(100.0 * t.idx_scan / (t.seq_scan + t.idx_scan), 2)
        END as index_usage_pct
    FROM pg_stat_user_tables t
    JOIN pg_class c ON c.oid = t.relid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
    ORDER BY t.seq_scan + t.idx_scan DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'schema': row[0],
            'table': row[1],
            'seq_scans': row[2],
            'seq_tuples_read': row[3],
            'index_scans': row[4],
            'index_tuples_fetched': row[5],
            'inserts': row[6],
            'updates': row[7],
            'deletes': row[8],
            'live_tuples': row[9],
            'dead_tuples': row[10],
            'index_usage_pct': row[11]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting table access patterns: {e}")
        return []

def get_bloated_tables(db_params, threshold_pct=20):
    """Identify tables with significant bloat.
    
    Args:
        db_params (dict): Database connection parameters
        threshold_pct (int): Minimum bloat percentage to report
        
    Returns:
        list: Bloated table information
    """
    query = f"""
    WITH table_bloat AS (
        SELECT 
            n.nspname as schemaname,
            c.relname as tablename,
            pg_relation_size(c.oid) as table_size,
            t.n_live_tup,
            t.n_dead_tup,
            CASE 
                WHEN t.n_live_tup = 0 THEN 0
                ELSE ROUND(100.0 * t.n_dead_tup / t.n_live_tup, 2)
            END as bloat_pct
        FROM pg_stat_user_tables t
        JOIN pg_class c ON c.oid = t.relid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
    )
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(table_size) as table_size,
        n_live_tup,
        n_dead_tup,
        bloat_pct
    FROM table_bloat
    WHERE bloat_pct >= {threshold_pct}
    ORDER BY bloat_pct DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'schema': row[0],
            'table': row[1],
            'size': row[2],
            'live_tuples': row[3],
            'dead_tuples': row[4],
            'bloat_pct': row[5]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting bloated tables: {e}")
        return []

def get_lock_analysis(db_params):
    """Analyze current database locks and blocking queries.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Lock and blocking information
    """
    query = """
    SELECT 
        blocked_locks.pid AS blocked_pid,
        blocked_activity.usename AS blocked_user,
        blocking_locks.pid AS blocking_pid,
        blocking_activity.usename AS blocking_user,
        blocked_activity.query AS blocked_query,
        blocking_activity.query AS blocking_query,
        blocked_activity.state AS blocked_state,
        blocking_activity.state AS blocking_state,
        EXTRACT(EPOCH FROM (now() - blocked_activity.query_start)) as blocked_duration_seconds
    FROM pg_locks blocked_locks
    JOIN pg_stat_activity blocked_activity ON blocked_locks.pid = blocked_activity.pid
    JOIN pg_locks blocking_locks 
        ON blocking_locks.locktype = blocked_locks.locktype
        AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
        AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
        AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
        AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
        AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
        AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
        AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
        AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
        AND blocking_locks.pid != blocked_locks.pid
    JOIN pg_stat_activity blocking_activity ON blocking_locks.pid = blocking_activity.pid
    WHERE NOT blocked_locks.granted
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'blocked_pid': row[0],
            'blocked_user': row[1],
            'blocking_pid': row[2],
            'blocking_user': row[3],
            'blocked_query': row[4][:100],
            'blocking_query': row[5][:100],
            'blocked_state': row[6],
            'blocking_state': row[7],
            'blocked_duration_seconds': row[8]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting lock analysis: {e}")
        return []

def get_uncompressed_hypertables(db_params):
    """Get hypertables without compression policies.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Uncompressed hypertable information
    """
    query = """
    SELECT 
        ht.hypertable_schema,
        ht.hypertable_name,
        ht.compression_enabled,
        pg_size_pretty(pg_total_relation_size(
            format('%%I.%%I', ht.hypertable_schema, ht.hypertable_name)::regclass
        )) as table_size
    FROM timescaledb_information.hypertables ht
    WHERE NOT ht.compression_enabled
    ORDER BY pg_total_relation_size(
        format('%%I.%%I', ht.hypertable_schema, ht.hypertable_name)::regclass
    ) DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'schema': row[0],
            'table': row[1],
            'compression_enabled': row[2],
            'size': row[3]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting uncompressed hypertables: {e}")
        return []

def get_compression_statistics(db_params):
    """Get compression effectiveness statistics for all compressed hypertables.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Compression statistics by hypertable
    """
    query = """
    WITH chunk_sizes AS (
        SELECT 
            c.hypertable_name,
            c.chunk_name,
            c.is_compressed,
            pg_total_relation_size(format('%%I.%%I', c.chunk_schema, c.chunk_name)::regclass) as chunk_size
        FROM timescaledb_information.chunks c
    ),
    compression_stats AS (
        SELECT 
            hypertable_name,
            COUNT(*) FILTER (WHERE is_compressed) as compressed_chunks,
            COUNT(*) FILTER (WHERE NOT is_compressed) as uncompressed_chunks,
            SUM(CASE WHEN is_compressed THEN chunk_size ELSE 0 END) as compressed_bytes,
            SUM(CASE WHEN NOT is_compressed THEN chunk_size ELSE 0 END) as uncompressed_bytes,
            SUM(chunk_size) as total_bytes
        FROM chunk_sizes
        GROUP BY hypertable_name
    )
    SELECT 
        hypertable_name,
        compressed_chunks,
        uncompressed_chunks,
        pg_size_pretty(compressed_bytes) as compressed_size,
        pg_size_pretty(uncompressed_bytes) as uncompressed_size,
        pg_size_pretty(total_bytes) as total_size,
        CASE 
            WHEN compressed_chunks > 0 AND uncompressed_chunks > 0 THEN
                ROUND(100.0 * compressed_bytes / NULLIF(uncompressed_bytes, 0), 2)
            ELSE NULL
        END as compression_ratio_pct
    FROM compression_stats
    WHERE compressed_chunks > 0
    ORDER BY total_bytes DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'table': row[0],
            'compressed_chunks': row[1],
            'uncompressed_chunks': row[2],
            'compressed_size': row[3],
            'uncompressed_size': row[4],
            'total_size': row[5],
            'compression_ratio_pct': row[6]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting compression statistics: {e}")
        return []

def get_chunk_distribution(db_params):
    """Get chunk distribution over time for all hypertables.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Chunk distribution information
    """
    query = """
    SELECT 
        c.hypertable_name,
        date_trunc('month', c.range_start) as month,
        COUNT(*) as chunk_count,
        pg_size_pretty(SUM(pg_total_relation_size(
            format('%%I.%%I', c.chunk_schema, c.chunk_name)::regclass
        ))) as total_size,
        MIN(c.range_start) as earliest_data,
        MAX(c.range_end) as latest_data
    FROM timescaledb_information.chunks c
    WHERE c.range_start IS NOT NULL
    GROUP BY c.hypertable_name, date_trunc('month', c.range_start)
    ORDER BY c.hypertable_name, month DESC
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'table': row[0],
            'month': row[1],
            'chunk_count': row[2],
            'total_size': row[3],
            'earliest_data': row[4],
            'latest_data': row[5]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting chunk distribution: {e}")
        return []

def get_background_job_statistics(db_params):
    """Get statistics for TimescaleDB background jobs.
    
    Args:
        db_params (dict): Database connection parameters
        
    Returns:
        list: Background job statistics
    """
    query = """
    SELECT 
        j.job_id,
        j.application_name,
        j.proc_name,
        j.schedule_interval,
        j.hypertable_schema,
        j.hypertable_name,
        js.last_run_started_at,
        js.last_successful_finish,
        js.total_runs,
        js.total_successes,
        js.total_failures,
        js.total_crashes,
        CASE 
            WHEN js.last_run_duration IS NOT NULL 
            THEN EXTRACT(EPOCH FROM js.last_run_duration) 
            ELSE NULL 
        END as last_run_duration_seconds
    FROM timescaledb_information.jobs j
    LEFT JOIN timescaledb_information.job_stats js ON j.job_id = js.job_id
    ORDER BY j.job_id
    """
    
    try:
        results = execute_query(db_params, query)
        return [{
            'job_id': row[0],
            'application_name': row[1],
            'proc_name': row[2],
            'schedule_interval': row[3],
            'hypertable_schema': row[4],
            'hypertable_name': row[5],
            'last_run_started': row[6],
            'last_successful_finish': row[7],
            'total_runs': row[8],
            'total_successes': row[9],
            'total_failures': row[10],
            'total_crashes': row[11],
            'last_run_duration_seconds': row[12]
        } for row in results]
    except Exception as e:
        logger.error(f"Error getting background job statistics: {e}")
        return []