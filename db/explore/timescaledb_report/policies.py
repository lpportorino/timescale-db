"""
Functions for handling TimescaleDB policies (compression, retention, refresh).
"""

import logging
import re
from timescaledb_report.db import check_if_schema_exists, safe_query
from timescaledb_report.hypertable import is_hypertable

logger = logging.getLogger(__name__)

def get_compression_info(db_params, table_name):
    """Get compression policy information for a given table

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get compression info for

    Returns:
        dict: Compression information or None if not compressed
    """
    if not is_hypertable(db_params, table_name):
        return None

    # Try newer TimescaleDB version first
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        result = safe_query(
            db_params,
            "SELECT * FROM timescaledb_information.compression_settings WHERE hypertable_name = %s;",
            (table_name,)
        )
        if result:
            return dict(result[0])

    # Fallback for older TimescaleDB versions
    result = safe_query(
        db_params,
        """
        SELECT
            true as is_compressed
        FROM _timescaledb_catalog.hypertable h
        WHERE h.schema_name = 'public'
          AND h.table_name = %s
          AND h.compressed_hypertable_id IS NOT NULL;
        """,
        (table_name,)
    )

    if not result:
        result = safe_query(
            db_params,
            """
            SELECT
                h.table_name,
                string_agg(DISTINCT a.attname, ', ') FILTER (WHERE cs.segmentby_column_index IS NOT NULL) as compress_segmentby,
                string_agg(DISTINCT a.attname || ' ' || CASE WHEN cs.orderby_asc THEN 'ASC' ELSE 'DESC' END, ', ')
                    FILTER (WHERE cs.orderby_column_index IS NOT NULL) as compress_orderby
            FROM _timescaledb_catalog.hypertable h
            JOIN _timescaledb_catalog.compression_settings cs ON h.id = cs.hypertable_id
            JOIN pg_attribute a ON a.attrelid = format('%%I.%%I', 'public', h.table_name)::regclass
                AND (a.attnum = cs.segmentby_column_index OR a.attnum = cs.orderby_column_index)
            WHERE h.schema_name = 'public' AND h.table_name = %s
            GROUP BY h.table_name;
            """,
            (table_name,)
        )

    if not result:
        return None

    return dict(result[0])

def get_retention_policy(db_params, table_name):
    """Get retention policy information for a given table

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get retention policy for

    Returns:
        dict: Retention policy information or None if no policy exists
    """
    if not is_hypertable(db_params, table_name):
        return None

    # Try newer TimescaleDB version first
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        result = safe_query(
            db_params,
            """
            SELECT * FROM timescaledb_information.jobs j
            WHERE j.hypertable_name = %s AND j.proc_name = 'policy_retention';
            """,
            (table_name,)
        )
        if result:
            return dict(result[0])

    # Fallback for older TimescaleDB versions
    result = safe_query(
        db_params,
        """
        SELECT
            j.id as job_id,
            j.schedule_interval,
            j.config
        FROM _timescaledb_config.bgw_job j
        JOIN _timescaledb_catalog.hypertable h ON j.hypertable_id = h.id
        WHERE j.proc_name = 'policy_retention'
        AND h.schema_name = 'public' AND h.table_name = %s;
        """,
        (table_name,)
    )

    if not result:
        # Try yet another approach for older versions
        result = safe_query(
            db_params,
            """
            SELECT
                j.id as job_id,
                j.schedule_interval,
                j.config
            FROM _timescaledb_config.bgw_job j
            WHERE j.proc_name = 'policy_retention'
            AND j.config::text LIKE %s;
            """,
            (f'%"{table_name}"%',)
        )

    return dict(result[0]) if result else None

def get_continuous_aggregates(db_params, table_name):
    """Get continuous aggregate information for a given table

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get continuous aggregates for

    Returns:
        list: List of continuous aggregate dictionaries or None if none exist
    """
    # Try newer TimescaleDB version first
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        # Check what columns are available
        columns = safe_query(
            db_params,
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'timescaledb_information'
              AND table_name = 'continuous_aggregates';
            """
        )

        if columns:
            # Build a query using the available columns
            column_names = [col['column_name'] for col in columns]
            logger.debug(f"Available columns in timescaledb_information.continuous_aggregates: {column_names}")

            # Check if we have the expected columns
            if 'hypertable_name' in column_names:
                # For TimescaleDB 2.x
                view_schema = 'view_schema' if 'view_schema' in column_names else ('user_view_schema' if 'user_view_schema' in column_names else "'public'")
                view_name = 'view_name' if 'view_name' in column_names else 'user_view_name'

                query = f"""
                SELECT
                    {view_schema} || '.' || {view_name} as view_name,
                    {view_name} as view_short_name,
                    'direct' as relationship_type
                FROM timescaledb_information.continuous_aggregates
                WHERE hypertable_name = %s;
                """

                result = safe_query(db_params, query, (table_name,))
                if result:
                    return [dict(r) for r in result]

    # Fallback for older TimescaleDB versions
    result = safe_query(
        db_params,
        """
        SELECT
            h.schema_name || '.' || h.table_name as hypertable_name,
            cagg.user_view_schema || '.' || cagg.user_view_name as view_name,
            cagg.user_view_name as view_short_name,
            'direct' as relationship_type,
            cagg.materialized_only
        FROM _timescaledb_catalog.hypertable h
        JOIN _timescaledb_catalog.continuous_agg cagg ON h.id = cagg.raw_hypertable_id
        WHERE h.schema_name = 'public' AND h.table_name = %s;
        """,
        (table_name,)
    )

    return [dict(r) for r in result] if result else None

def get_all_continuous_aggregates(db_params):
    """Get all continuous aggregates with their source tables, including multi-level relationships

    Args:
        db_params (dict): Database connection parameters

    Returns:
        dict: Information about continuous aggregates including chained relationships
    """
    result = []
    agg_chain = {}
    materialized_tables = {}
    mat_to_view_mapping = {}  # Mapping from materialized tables to user views
    view_definitions = {}

    # STEP 1: Get the view definitions from timescaledb_information.continuous_aggregates
    # This gives us the true SQL definitions that show the dependencies
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        view_def_query = """
        SELECT
            view_name,
            view_definition
        FROM timescaledb_information.continuous_aggregates
        """
        view_defs = safe_query(db_params, view_def_query)
        if view_defs:
            logger.debug(f"Found {len(view_defs)} continuous aggregate view definitions")
            for row in view_defs:
                if 'view_name' in row and 'view_definition' in row:
                    view_name = row['view_name']
                    view_def = row['view_definition']
                    view_definitions[view_name] = view_def
                    logger.debug(f"Stored view definition for {view_name} (length: {len(view_def)})")

    # Also get view definitions from pg_get_viewdef for views not in TimescaleDB's continuous aggregates
    view_query = """
    SELECT
        c.relname AS view_name,
        pg_get_viewdef(c.oid) AS definition
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'v'
      AND n.nspname = 'public'
    """

    views = safe_query(db_params, view_query)
    if views:
        logger.debug(f"Found {len(views)} views using pg_get_viewdef")
        for view in views:
            if 'view_name' in view and 'definition' in view:
                view_name = view['view_name']
                if view_name not in view_definitions:  # Don't overwrite existing definitions
                    view_definitions[view_name] = view['definition']
                    logger.debug(f"Added view definition for '{view_name}' from pg_get_viewdef")

    # STEP 2: Get the mapping between materialized hypertables and user views
    mat_view_query = """
    SELECT
        h.schema_name || '.' || h.table_name as mat_hypertable,
        h.table_name as mat_hypertable_short,
        cagg.user_view_schema || '.' || cagg.user_view_name as view_name,
        cagg.user_view_name as view_name_short
    FROM _timescaledb_catalog.hypertable h
    JOIN _timescaledb_catalog.continuous_agg cagg ON h.id = cagg.mat_hypertable_id
    WHERE h.schema_name = '_timescaledb_internal'
    """

    mat_views = safe_query(db_params, mat_view_query)
    if mat_views:
        logger.debug(f"Found {len(mat_views)} materialized hypertable to view mappings")
        for row in mat_views:
            if 'mat_hypertable' in row and 'view_name' in row:
                mat_table = row['mat_hypertable']
                mat_short = row['mat_hypertable_short']
                view_name = row['view_name']
                view_short = row['view_name_short']

                # Store in materialized_tables
                materialized_tables[mat_table] = {
                    'view_name': view_name,
                    'view_name_short': view_short
                }

                # Create reverse mapping from materialized table to view
                mat_to_view_mapping[mat_short] = view_short
                logger.debug(f"Materialized mapping: {mat_short} -> {view_short}")

    # STEP 3: Get direct aggregate relationships
    # Try newer TimescaleDB version first
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        # Check what columns are available
        columns = safe_query(
            db_params,
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'timescaledb_information'
              AND table_name = 'continuous_aggregates';
            """
        )

        if columns:
            column_names = [col['column_name'] for col in columns]
            logger.debug(f"Available columns in timescaledb_information.continuous_aggregates: {column_names}")

            if 'hypertable_name' in column_names:
                # For TimescaleDB 2.x
                hypertable_schema = 'hypertable_schema' if 'hypertable_schema' in column_names else "'public'"
                hypertable_name = 'hypertable_name'
                view_schema = 'view_schema' if 'view_schema' in column_names else ('user_view_schema' if 'user_view_schema' in column_names else "'public'")
                view_name = 'view_name' if 'view_name' in column_names else 'user_view_name'

                query = f"""
                SELECT
                    {hypertable_schema} || '.' || {hypertable_name} as raw_table,
                    {hypertable_name} as raw_table_name,
                    {view_schema} || '.' || {view_name} as agg_view,
                    {view_name} as agg_view_name,
                    'direct' as relationship_type
                FROM timescaledb_information.continuous_aggregates
                """

                direct_aggs = safe_query(db_params, query)
                if direct_aggs:
                    logger.debug(f"Found {len(direct_aggs)} direct continuous aggregates")
                    for row in direct_aggs:
                        relationship = dict(row)
                        result.append(relationship)

                        # Add to agg_chain
                        table_name = relationship['raw_table_name']
                        agg_name = relationship['agg_view_name']

                        if table_name not in agg_chain:
                            agg_chain[table_name] = {'direct': [], 'indirect': []}

                        agg_chain[table_name]['direct'].append(agg_name)
                        logger.debug(f"Added direct relationship: {table_name} -> {agg_name}")

    # STEP 4: Analyze view definitions to find chained relationships
    chained_aggs = []

    # Process all view definitions to find dependencies
    for view_name, definition in view_definitions.items():
        for other_view_name in view_definitions.keys():
            if view_name != other_view_name and other_view_name in definition:
                # Found a dependency in the view definition
                logger.debug(f"Found dependency in view definition: {view_name} depends on {other_view_name}")

                chained_aggs.append({
                    'raw_table_name': other_view_name,
                    'agg_view_name': view_name,
                    'relationship_type': 'chained'
                })

    # STEP 5: Process chained relationships to build the complete chain
    for chain in chained_aggs:
        source = chain['raw_table_name']
        target = chain['agg_view_name']
        logger.debug(f"Processing chained relationship: {source} -> {target}")

        # Add this chained relationship to the result
        result.append({
            'raw_table': source,
            'raw_table_name': source,
            'agg_view': target,
            'agg_view_name': target,
            'relationship_type': 'chained'
        })

        # Find all tables that have source as a direct aggregate
        for base_table, aggs in agg_chain.items():
            if source in aggs['direct']:
                # This is an indirect relationship to the original base table
                if 'indirect' not in agg_chain[base_table]:
                    agg_chain[base_table]['indirect'] = []
                if target not in agg_chain[base_table]['indirect']:
                    agg_chain[base_table]['indirect'].append(target)
                    logger.debug(f"Added indirect relationship: {base_table} -> {source} -> {target}")

    # Special handling for multi-level chains - we need to do this in multiple passes
    # to catch deeply nested chains
    for _ in range(3):  # Do up to 3 passes to catch chains up to level 4
        chains_found = 0
        for chain in chained_aggs:
            source = chain['raw_table_name']
            target = chain['agg_view_name']

            # Look for any table that has 'source' as an indirect aggregate
            for base_table, aggs in agg_chain.items():
                if source in aggs.get('indirect', []):
                    # If source is an indirect aggregate, then target is also an indirect aggregate
                    if 'indirect' not in agg_chain[base_table]:
                        agg_chain[base_table]['indirect'] = []
                    if target not in agg_chain[base_table]['indirect']:
                        agg_chain[base_table]['indirect'].append(target)
                        logger.debug(f"Added deep chain: {base_table} -> [..] -> {source} -> {target}")
                        chains_found += 1

        if chains_found == 0:
            break

    # STEP 6: Build a dependency graph for path-finding
    graph = {}
    for row in result:
        if 'raw_table_name' in row and 'agg_view_name' in row:
            source = row['raw_table_name']
            target = row['agg_view_name']

            if source not in graph:
                graph[source] = []
            if target not in graph[source]:
                graph[source].append(target)
                logger.debug(f"Added to dependency graph: {source} -> {target}")

    # STEP 7: Fix TimescaleDB continuous aggregate chains by direct table introspection
    # This handles the case where views reference internal materialized tables
    # Fixed query to use h.id instead of v.id to avoid the "column v.id does not exist" error
    cagg_query = """
    SELECT
        h.schema_name || '.' || h.table_name as raw_table,
        h.table_name as raw_table_name,
        v.raw_hypertable_id as raw_id,
        h.id as cagg_id,
        v.user_view_name as view_name
    FROM _timescaledb_catalog.continuous_agg v
    JOIN _timescaledb_catalog.hypertable h ON h.id = v.raw_hypertable_id
    WHERE h.schema_name = 'public'
    ORDER BY h.id
    """
    caggs = safe_query(db_params, cagg_query)

    if caggs:
        logger.debug(f"Found {len(caggs)} continuous aggregates from catalog")

        # List them for debugging
        for cagg in caggs:
            logger.debug(f"Catalog cagg: {cagg}")

        # Find multi-level chains by correlating IDs
        # First, build a mapping from raw_id to all views that use it
        raw_to_views = {}
        for cagg in caggs:
            raw_id = cagg['raw_id']
            view_name = cagg['view_name']

            if raw_id not in raw_to_views:
                raw_to_views[raw_id] = []
            raw_to_views[raw_id].append(view_name)

        # Check specifically for health metrics chain
        health_views = []
        for cagg in caggs:
            if cagg['view_name'].startswith('health_metrics_'):
                health_views.append(cagg['view_name'])

        # Sort them by level (1min, 1hour, 1day)
        health_views.sort()
        logger.debug(f"Found health metrics views: {health_views}")

        if len(health_views) >= 2:
            # Assume they form a chain from raw → 1min → 1hour → 1day
            if 'health_metrics_raw' in agg_chain:
                for i in range(1, len(health_views)):
                    previous = health_views[i-1]
                    current = health_views[i]

                    # Check if this view is already in the chain
                    if current not in agg_chain['health_metrics_raw'].get('direct', []) and \
                       current not in agg_chain['health_metrics_raw'].get('indirect', []):
                        # Add it as an indirect dependency
                        if 'indirect' not in agg_chain['health_metrics_raw']:
                            agg_chain['health_metrics_raw']['indirect'] = []

                        agg_chain['health_metrics_raw']['indirect'].append(current)
                        logger.debug(f"Added missing health metrics chain link: health_metrics_raw -> {current}")

    return {
        'agg_relationships': result,
        'agg_chain': agg_chain,
        'materialized_tables': materialized_tables,
        'view_definitions': view_definitions,
        'dependency_graph': graph
    }

def get_refresh_policies(db_params):
    """Get refresh policies for continuous aggregates

    Args:
        db_params (dict): Database connection parameters

    Returns:
        list: List of refresh policy dictionaries or None if none exist
    """
    # For newer TimescaleDB version
    if check_if_schema_exists(db_params, 'timescaledb_information'):
        result = safe_query(
            db_params,
            "SELECT * FROM timescaledb_information.continuous_aggregate_policies;"
        )
        if result:
            return [dict(r) for r in result]

    # Fallback for older TimescaleDB versions - simplified
    result = safe_query(
        db_params,
        """
        SELECT
            j.id as job_id,
            j.schedule_interval,
            j.config
        FROM _timescaledb_config.bgw_job j
        WHERE j.proc_name = 'policy_refresh_continuous_aggregate';
        """
    )

    return [dict(r) for r in result] if result else None
