"""
Functions for generating Markdown reports focused on database schema and context.
"""

import logging
from datetime import datetime
from tabulate import tabulate

from timescaledb_report.strings import get_string
from timescaledb_report.db import get_timescaledb_version
from timescaledb_report.schema import get_all_tables, get_table_schema, get_indexes
from timescaledb_report.hypertable import is_hypertable, get_hypertable_info
from timescaledb_report.policies import get_continuous_aggregates, get_all_continuous_aggregates
from timescaledb_report.descriptions import (
    get_table_purpose,
    get_column_purpose,
    get_index_purpose
)
from timescaledb_report.stats import (
    get_database_health_score,
    get_connection_statistics,
    get_slow_queries,
    get_unused_indexes,
    get_index_usage_statistics,
    get_table_access_patterns,
    get_bloated_tables,
    get_uncompressed_hypertables,
    get_compression_statistics,
    get_chunk_distribution,
    get_background_job_statistics
)

logger = logging.getLogger(__name__)

def format_markdown_table(headers, rows):
    """Use tabulate to create a well-formatted markdown table"""
    return tabulate(rows, headers=headers, tablefmt="pipe")

def generate_toc(tables):
    """Generate a table of contents for the tables"""
    toc = [f"## {get_string('report.sections.table_of_contents', 'Table of Contents')}\n"]
    for table in sorted(tables):
        # Use underscores in anchors to match how HTML ids are generated
        anchor = table.lower()
        toc.append(f"- [{table}](#{anchor})")
    return "\n".join(toc)

def build_aggregate_chains(agg_chain, view_definitions, dependency_graph=None):
    """Build complete chains of continuous aggregates, showing multi-level dependencies

    Args:
        agg_chain (dict): Dictionary of tables and their aggregates
        view_definitions (dict): Dictionary of view definitions
        dependency_graph (dict, optional): Graph representation of dependencies

    Returns:
        dict: Dictionary mapping each base table to its complete aggregate chain
    """
    logger.debug("Starting to build aggregate chains")
    logger.debug(f"Input agg_chain has {len(agg_chain)} base tables")
    logger.debug(f"Input view_definitions has {len(view_definitions)} views")
    if dependency_graph:
        logger.debug(f"Input dependency_graph has {len(dependency_graph)} nodes")

    # Start with a copy of the agg_chain
    complete_chains = {}

    # For each base table with aggregates
    for table, aggregates in agg_chain.items():
        direct_aggs = aggregates.get('direct', [])
        indirect_aggs = aggregates.get('indirect', [])

        logger.debug(f"Processing table: {table}")
        logger.debug(f"  Direct aggregates: {direct_aggs}")
        logger.debug(f"  Indirect aggregates: {indirect_aggs}")

        if direct_aggs:
            # Initialize the chain for this table
            if table not in complete_chains:
                complete_chains[table] = {}

            # Add direct aggregates as first level
            for agg in direct_aggs:
                complete_chains[table][agg] = {'level': 1, 'source': table, 'children': []}
                logger.debug(f"  Added direct level 1: {table} -> {agg}")

            # Process indirect aggregates
            for indirect in indirect_aggs:
                logger.debug(f"  Processing indirect aggregate: {indirect}")
                # Find which direct aggregate this is based on by checking view definitions
                for direct in direct_aggs:
                    if indirect in view_definitions and direct in view_definitions[indirect]:
                        level = 2  # Default to level 2
                        source = direct
                        logger.debug(f"    Found in view definition: {indirect} depends on {direct}")

                        # Add to the chain
                        if direct in complete_chains[table]:
                            complete_chains[table][direct]['children'].append(indirect)
                            logger.debug(f"    Added as child: {direct} -> {indirect}")

                            # Also add as a separate entry
                            complete_chains[table][indirect] = {
                                'level': level,
                                'source': source,
                                'children': []
                            }
                            logger.debug(f"    Set {indirect} at level {level}, source={source}")

                # Check for level 3+ relationships (recursive)
                for level2_agg in indirect_aggs:
                    if indirect != level2_agg and indirect in view_definitions and level2_agg in view_definitions[indirect]:
                        # This is a level 3+ relationship
                        level = 3
                        source = level2_agg
                        logger.debug(f"    Found level 3+ relationship: {indirect} depends on {level2_agg}")

                        # Update the chain
                        if level2_agg in complete_chains[table]:
                            complete_chains[table][level2_agg]['children'].append(indirect)
                            logger.debug(f"    Added as level 3 child: {level2_agg} -> {indirect}")

                            # Add/update the entry
                            complete_chains[table][indirect] = {
                                'level': level,
                                'source': source,
                                'children': []
                            }
                            logger.debug(f"    Set {indirect} at level {level}, source={source}")

    # If there are missing connections in the chain, try to complete them using the view definitions
    # This is the improved part to better handle chained aggregates
    logger.debug("Looking for missing connections in chains using view definitions")
    for table in complete_chains:
        # Get all views in this chain
        views = list(complete_chains[table].keys())
        logger.debug(f"Table {table} chain has views: {views}")

        # Iterate through views to find potential dependencies
        for view in views:
            view_def = view_definitions.get(view, "")
            if view_def:
                logger.debug(f"Checking view definition for {view} (length: {len(view_def)})")
            else:
                logger.debug(f"No view definition found for {view}")

            # Look for "FROM view_name" patterns
            for other_view in views:
                if view != other_view and other_view in view_def:
                    # Found a dependency: other_view is used by view
                    # Update level and source
                    other_view_level = complete_chains[table][other_view]['level']
                    new_level = other_view_level + 1
                    logger.debug(f"Found dependency in view definition: {view} uses {other_view}")
                    logger.debug(f"  {other_view} is at level {other_view_level}, so {view} should be at level {new_level}")

                    # Update view level and source if we found a closer relationship
                    if complete_chains[table][view]['level'] < new_level:
                        logger.debug(f"  Updating {view} level from {complete_chains[table][view]['level']} to {new_level}")
                        logger.debug(f"  Updating {view} source from {complete_chains[table][view]['source']} to {other_view}")
                        complete_chains[table][view]['level'] = new_level
                        complete_chains[table][view]['source'] = other_view

                        # Update children lists
                        if view not in complete_chains[table][other_view]['children']:
                            complete_chains[table][other_view]['children'].append(view)
                            logger.debug(f"  Added {view} as child of {other_view}")

    # If we have a dependency graph, use it to enhance our chain information
    if dependency_graph:
        logger.debug("Using dependency graph to enhance chain information")
        for table in complete_chains:
            # For each view in the chain, check if we need to update its level
            for view_name in list(complete_chains[table].keys()):
                # Skip the table itself
                if view_name == table:
                    continue

                # Use the dependency graph to find the actual path length
                path = find_path_in_graph(dependency_graph, table, view_name)
                if path:
                    # The level is the path length (number of hops)
                    logger.debug(f"Found path in graph: {table} -> {view_name}: {path}")
                    logger.debug(f"  Path length: {len(path)}, setting level to {len(path) - 1}")
                    complete_chains[table][view_name]['level'] = len(path) - 1

                    # If this is a multi-level view, find its immediate source
                    if len(path) > 2:
                        logger.debug(f"  Multi-level view, immediate source is {path[-2]}")
                        complete_chains[table][view_name]['source'] = path[-2]
                else:
                    logger.debug(f"No path found in graph: {table} -> {view_name}")

    # Debug specifically for health_metrics_raw
    if 'health_metrics_raw' in complete_chains:
        logger.debug("HEALTH METRICS CHAIN DETAILS:")
        for view, details in complete_chains['health_metrics_raw'].items():
            logger.debug(f"  View: {view}")
            logger.debug(f"    Level: {details['level']}")
            logger.debug(f"    Source: {details['source']}")
            logger.debug(f"    Children: {details['children']}")
    else:
        logger.debug("health_metrics_raw not found in complete_chains")

    logger.debug(f"Final chains built for {len(complete_chains)} tables")
    return complete_chains

def find_path_in_graph(graph, start, end, path=None):
    """Find a path from start to end in a graph using depth-first search

    Args:
        graph (dict): Graph representation where keys are nodes and values are lists of neighbors
        start (str): Starting node
        end (str): Ending node
        path (list, optional): Current path being explored

    Returns:
        list: Path from start to end or None if no path exists
    """
    if path is None:
        path = []

    # Make a copy of the path to avoid modifying the original
    path = path + [start]

    # If we've reached the end, return the path
    if start == end:
        return path

    # If start isn't in the graph, there's no path
    if start not in graph:
        return None

    # Try all neighbors
    for node in graph.get(start, []):
        # Skip already visited nodes
        if node not in path:
            # Recursively find path
            new_path = find_path_in_graph(graph, node, end, path)
            if new_path:
                return new_path

    # No path found
    return None

def format_aggregate_chain(chains, base_table):
    """Format the aggregate chain for display in the report

    Args:
        chains (dict): Complete chains dictionary from build_aggregate_chains
        base_table (str): The base table to format chains for

    Returns:
        str: Formatted chain suitable for Markdown inclusion
    """
    if base_table not in chains:
        logger.debug(f"No chain found for base table {base_table}")
        return ""

    # Get all views in the chain
    views = chains[base_table]
    logger.debug(f"Formatting chain for {base_table} with {len(views)} views")

    # Build a tree structure
    tree = {}

    # First, group views by level
    level_groups = {}
    for view_name, view_info in views.items():
        level = view_info['level']
        if level not in level_groups:
            level_groups[level] = []
        level_groups[level].append((view_name, view_info))
        logger.debug(f"  {view_name} at level {level}")

    # Build the chain text
    lines = []

    # Start with the base table
    base_table_text = get_string("report.values.base_table", "base table")
    lines.append(f"`{base_table}` ({base_table_text})")

    # Add each level, indented appropriately
    for level in sorted(level_groups.keys()):
        for view_name, view_info in sorted(level_groups[level]):
            source = view_info['source']
            indent = "    " * (level - 1)

            level_text = get_string("report.values.level", "level")
            sourced_text = get_string("report.values.sourced_from", "sourced from")

            lines.append(f"{indent}↳ `{view_name}` ({level_text} {level}, {sourced_text} `{source}`)")
            logger.debug(f"  Added line: {indent}↳ {view_name} (level {level}, from {source})")

    return "\n".join(lines)

def get_continuous_aggregates_for_table(db_params, table_name, agg_info=None):
    """Get all continuous aggregates for a table, including chained ones

    Args:
        db_params (dict): Database connection parameters
        table_name (str): Table name to get aggregates for
        agg_info (dict): Optional pre-loaded aggregate information

    Returns:
        dict: Dictionary with direct and indirect continuous aggregates
    """
    logger.debug(f"Getting continuous aggregates for table {table_name}")

    # If we don't have pre-loaded aggregate info, get it now
    if not agg_info:
        try:
            logger.debug("No pre-loaded agg_info, retrieving now")
            agg_info = get_all_continuous_aggregates(db_params)
        except Exception as e:
            logger.warning(f"Error retrieving continuous aggregate information: {e}")
            agg_info = {'agg_chain': {}, 'view_definitions': {}, 'dependency_graph': {}}

    # Extract agg_chain, view_definitions, and dependency_graph
    agg_chain = agg_info.get('agg_chain', {})
    view_definitions = agg_info.get('view_definitions', {})
    dependency_graph = agg_info.get('dependency_graph', {})

    logger.debug(f"agg_chain has {len(agg_chain)} entries")
    logger.debug(f"view_definitions has {len(view_definitions)} entries")
    if dependency_graph:
        logger.debug(f"dependency_graph has {len(dependency_graph)} nodes")

    # Debug view definitions for health metrics views
    for view_name in ['health_metrics_1min_cagg', 'health_metrics_1hour_cagg', 'health_metrics_1day_cagg']:
        if view_name in view_definitions:
            definition = view_definitions[view_name]
            logger.debug(f"{view_name} definition exists: {len(definition)} chars")
            # Check what it references
            for other_view in ['health_metrics_raw', 'health_metrics_1min_cagg', 'health_metrics_1hour_cagg']:
                if other_view in definition:
                    logger.debug(f"  - Definition of {view_name} references {other_view}")

    # Build complete chains
    chains = build_aggregate_chains(agg_chain, view_definitions, dependency_graph)

    # Prepare result
    result = {
        'direct': [],
        'indirect': [],
        'complete_chains': chains
    }

    # Get direct and indirect aggregates for this table
    if table_name in agg_chain:
        logger.debug(f"Found table {table_name} in agg_chain")
        if 'direct' in agg_chain[table_name]:
            result['direct'] = agg_chain[table_name]['direct']
            logger.debug(f"  Direct aggregates: {result['direct']}")
        if 'indirect' in agg_chain[table_name]:
            result['indirect'] = agg_chain[table_name]['indirect']
            logger.debug(f"  Indirect aggregates: {result['indirect']}")
    else:
        logger.debug(f"Table {table_name} not found in agg_chain")

    # If we couldn't find any aggregates, try the fallback method
    if not result['direct'] and not result['indirect']:
        logger.debug(f"No aggregates found for {table_name}, trying fallback method")
        try:
            direct_aggs = get_continuous_aggregates(db_params, table_name)
            if direct_aggs:
                logger.debug(f"Fallback found {len(direct_aggs)} direct aggregates")
                for agg in direct_aggs:
                    if 'view_short_name' in agg:
                        result['direct'].append(agg['view_short_name'])
                        logger.debug(f"  Added direct: {agg['view_short_name']}")
                    elif 'view_name' in agg:
                        # Extract just the name part if it includes schema
                        view_name = agg['view_name']
                        if '.' in view_name:
                            view_name = view_name.split('.')[-1]
                        result['direct'].append(view_name)
                        logger.debug(f"  Added direct: {view_name}")
            else:
                logger.debug("Fallback method found no aggregates")
        except Exception as e:
            logger.warning(f"Error retrieving direct continuous aggregates: {e}")

    return result

def generate_markdown(db_params, output_file):
    """Generate schema-focused markdown report

    Args:
        db_params (dict): Database connection parameters
        output_file (str): Output file path

    Returns:
        bool: True if report generated successfully
    """
    tables = get_all_tables(db_params)
    timescaledb_version = get_timescaledb_version(db_params)

    logger.info(get_string("log_messages.found_tables", "Found {count} tables", count=len(tables)))

    # Get all continuous aggregate relationships
    try:
        logger.debug(get_string("log_messages.retrieving_aggregates",
                               "Retrieving all continuous aggregate relationships"))
        all_aggs = get_all_continuous_aggregates(db_params)
        agg_chain = all_aggs.get('agg_chain', {})
        view_definitions = all_aggs.get('view_definitions', {})
        dependency_graph = all_aggs.get('dependency_graph', {})

        logger.debug(get_string("log_messages.retrieved_info",
                               "Retrieved aggregate info: {chain_count} chains, {view_count} view definitions",
                               chain_count=len(agg_chain),
                               view_count=len(view_definitions)))
    except Exception as e:
        logger.warning(get_string("log_messages.error_aggregates",
                                 "Error retrieving continuous aggregate relationships: {error}",
                                 error=e))
        all_aggs = {}
        agg_chain = {}
        view_definitions = {}
        dependency_graph = {}

    # Build the report content
    content = []

    # Header
    content.append(f"# {get_string('report.title', 'TimescaleDB Database Schema')}\n")
    content.append(get_string("report.generated_on", "Generated on: {date}",
                             date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    content.append(get_string("report.database_info", "Database: {dbname} @ {host}:{port}",
                             dbname=db_params['dbname'],
                             host=db_params['host'],
                             port=db_params['port']))
    content.append(get_string("report.timescaledb_version", "TimescaleDB Version: {version}",
                             version=timescaledb_version if timescaledb_version else 'Unknown'))
    content.append("")  # Empty line
    
    # Executive Summary
    content.append(f"## {get_string('report.executive_summary.header', 'Executive Summary')}\n")
    
    # Get health score and metrics
    health_info = get_database_health_score(db_params)
    if health_info['score'] is not None:
        content.append(get_string("report.executive_summary.database_health", 
                                 "Database Health Score: {score}/100",
                                 score=health_info['score']))
        content.append("")
        
        if health_info['issues']:
            content.append(f"### {get_string('report.executive_summary.critical_issues', 'Critical Issues')}")
            for issue in health_info['issues']:
                content.append(f"- {issue}")
            content.append("")
        
        if health_info['warnings']:
            content.append(f"### {get_string('report.executive_summary.warnings', 'Warnings')}")
            for warning in health_info['warnings']:
                content.append(f"- {warning}")
            content.append("")
    
    # Key metrics
    content.append(f"### {get_string('report.executive_summary.key_metrics', 'Key Metrics')}")
    
    # Get database size
    from timescaledb_report.db import get_database_size_info
    db_size_info = get_database_size_info(db_params)
    if db_size_info:
        content.append(f"- {get_string('report.executive_summary.total_size', 'Total Database Size: {size}', size=db_size_info['total_size'])}")
    
    # Count continuous aggregates
    agg_count = len([t for t in agg_chain.values() if t.get('direct') or t.get('indirect')])
    content.append(f"- {get_string('report.executive_summary.continuous_aggregate_count', 'Continuous Aggregates: {count}', count=agg_count)}")
    
    # Count indexes
    total_indexes = 0
    for table in tables:
        indexes = get_indexes(db_params, table)
        total_indexes += len(indexes)
    content.append(f"- {get_string('report.executive_summary.index_count', 'Total Indexes: {count}', count=total_indexes)}")
    
    # Count unused indexes
    unused_indexes = get_unused_indexes(db_params)
    if unused_indexes:
        content.append(f"- {get_string('report.executive_summary.unused_index_count', 'Unused Indexes: {count}', count=len(unused_indexes))}")
    
    content.append("")  # Empty line

    # Overview
    content.append(f"## {get_string('report.overview.header', 'Overview')}\n")

    content.append(get_string("report.overview.intro",
                             "This database contains {table_count} tables and uses TimescaleDB for time-series data storage.",
                             table_count=len(tables)))

    # Count hypertables and regular tables
    hypertable_count = 0
    for table in tables:
        if is_hypertable(db_params, table):
            hypertable_count += 1

    content.append(get_string("report.overview.hypertable_count",
                             "There are {hypertable_count} TimescaleDB hypertables and {regular_count} regular tables.",
                             hypertable_count=hypertable_count,
                             regular_count=len(tables) - hypertable_count))
    content.append("")  # Empty line

    content.append(get_string("report.overview.pattern_description",
                             """The tables primarily store time-series data using a consistent pattern:
- Most tables have a `time` column with timestamp type
- Many tables use JSONB columns for flexible schema storage
- Tables are indexed for efficient time-based queries
- Some tables have continuous aggregates for downsampling time-series data"""))
    content.append("")  # Empty line

    # Add table of contents
    content.append(generate_toc(tables))
    content.append("\n")
    
    # Performance Metrics Section
    content.append(f"\n## {get_string('report.performance.header', 'Performance Metrics')}\n")
    
    # Connection statistics
    conn_stats = get_connection_statistics(db_params)
    if conn_stats:
        content.append(f"### {get_string('report.performance.connection_statistics', 'Connection Statistics')}")
        conn_headers = ["State", "Count", "Max Duration"]
        conn_rows = []
        for stat in conn_stats:
            duration = f"{stat['max_duration_seconds']:.1f}s" if stat['max_duration_seconds'] else "N/A"
            conn_rows.append([stat['state'], stat['count'], duration])
        content.append(format_markdown_table(conn_headers, conn_rows))
        content.append("")
    
    # Slow queries
    slow_queries = get_slow_queries(db_params, limit=10)
    if slow_queries:
        content.append(f"### {get_string('report.performance.slow_queries', 'Slowest Queries (by average execution time)')}")
        query_headers = ["Query Preview", "Calls", "Avg Time (ms)", "Total Time (ms)"]
        query_rows = []
        for q in slow_queries[:5]:  # Show top 5
            query_rows.append([
                q['query'][:50] + "...",
                q['calls'],
                f"{q['mean_exec_time']:.2f}",
                f"{q['total_exec_time']:.2f}"
            ])
        content.append(format_markdown_table(query_headers, query_rows))
        content.append("")
    
    # Storage Optimization Section
    content.append(f"\n## {get_string('report.storage.header', 'Storage Optimization')}\n")
    
    # Compression statistics
    compression_stats = get_compression_statistics(db_params)
    if compression_stats:
        content.append(f"### {get_string('report.storage.compression_effectiveness', 'Compression Effectiveness by Table')}")
        comp_headers = ["Table", "Compressed Chunks", "Uncompressed Chunks", "Total Size", "Compression Ratio"]
        comp_rows = []
        for stat in compression_stats:
            ratio = f"{stat['compression_ratio_pct']}%" if stat['compression_ratio_pct'] else "N/A"
            comp_rows.append([
                stat['table'],
                stat['compressed_chunks'],
                stat['uncompressed_chunks'],
                stat['total_size'],
                ratio
            ])
        content.append(format_markdown_table(comp_headers, comp_rows))
        content.append("")
    
    # Uncompressed hypertables
    uncompressed = get_uncompressed_hypertables(db_params)
    if uncompressed:
        content.append(f"### {get_string('report.storage.uncompressed_tables', 'Tables Without Compression')}")
        uncomp_headers = ["Table", "Size"]
        uncomp_rows = [[u['table'], u['size']] for u in uncompressed]
        content.append(format_markdown_table(uncomp_headers, uncomp_rows))
        content.append("")

    # Tables summary section header
    content.append(f"\n## {get_string('report.sections.tables_summary', 'Tables Summary')}\n")

    # Get headers from config
    headers = get_string("report.table_headers.summary_headers",
                        ["Table Name", "TimescaleDB Hypertable", "Primary Time Column",
                         "Contains JSON/JSONB", "Aggregation Views", "Purpose"])
    rows = []

    # Values for yes/no fields
    yes_text = get_string("report.values.yes", "Yes")
    no_text = get_string("report.values.no", "No")
    none_text = get_string("report.values.none", "None")
    na_text = get_string("report.values.na", "N/A")

    # Collect data for table summary
    for table in sorted(tables):
        # Get schema and index info
        schema = get_table_schema(db_params, table)
        is_hyper = is_hypertable(db_params, table)

        # Check for time column and JSON columns
        has_time_column = False
        time_column_name = "time"  # Assume default
        has_json = False

        for col in schema:
            if col['name'].lower() == 'time':
                has_time_column = True
                time_column_name = col['name']
            if 'json' in col['type'].lower():
                has_json = True

        # Get aggregation views - combine direct and indirect
        aggregates = get_continuous_aggregates_for_table(db_params, table, all_aggs)
        aggs = aggregates['direct'] + aggregates['indirect']

        # Add to table summary
        purpose = get_table_purpose(table)
        rows.append([
            table,
            yes_text if is_hyper else no_text,
            time_column_name if has_time_column else na_text,
            yes_text if has_json else no_text,
            ", ".join(aggs) if aggs else none_text,
            purpose
        ])

    # Add the table summary
    content.append(format_markdown_table(headers, rows))

    # Table details section header
    content.append(f"\n## {get_string('report.sections.table_details', 'Table Details')}\n")

    # Add table details
    for table in sorted(tables):
        # Get schema and index info
        schema = get_table_schema(db_params, table)
        indexes = get_indexes(db_params, table)
        is_hyper = is_hypertable(db_params, table)

        # Check for JSON columns
        has_json = False
        for col in schema:
            if 'json' in col['type'].lower():
                has_json = True
                break

        # Get aggregation information
        aggregates = get_continuous_aggregates_for_table(db_params, table, all_aggs)
        direct_aggs = aggregates['direct']
        indirect_aggs = aggregates['indirect']
        complete_chains = aggregates.get('complete_chains', {})

        # Add anchor and table name - use the table name directly as the ID
        anchor = table.lower()
        content.append(f"### {table} {{#{anchor}}}\n")

        # Add table purpose description
        purpose = get_table_purpose(table)
        purpose_label = get_string("report.sections.purpose_label", "Purpose")
        content.append(f"**{purpose_label}:** {purpose}\n")

        # Add TimescaleDB info if applicable
        if is_hyper:
            hyper_info = get_hypertable_info(db_params, table)
            time_column = hyper_info.get('time_column') if hyper_info else None

            hypertable_label = get_string("report.sections.timescaledb_hypertable_label",
                                         "TimescaleDB Hypertable")

            if time_column:
                content.append(f"**{hypertable_label}:** {yes_text}, using `{time_column}` as time column\n")
            else:
                content.append(f"**{hypertable_label}:** {yes_text}\n")

            # Display continuous aggregates with hierarchy information
            if direct_aggs or indirect_aggs:
                # If we have both direct and indirect aggregates, we're a base table for an aggregate chain
                # Use the formatted aggregate chain for more clarity
                if table in complete_chains:
                    logger.debug(f"Formatting aggregate chain for {table}")

                    chain_label = get_string("report.sections.continuous_aggregate_chain",
                                           "Continuous Aggregate Chain")

                    content.append(f"**{chain_label}:**\n")
                    content.append("```")
                    chain_text = format_aggregate_chain(complete_chains, table)
                    content.append(chain_text)
                    content.append("```\n")
                    logger.debug(f"Generated chain text:\n{chain_text}")
                else:
                    # Just list direct aggregates as before
                    if direct_aggs:
                        agg_list = ", ".join([f"`{agg}`" for agg in direct_aggs])

                        direct_aggs_label = get_string("report.sections.direct_continuous_aggregates",
                                                      "Direct Continuous Aggregates")

                        content.append(f"**{direct_aggs_label}:** {agg_list}\n")
                        logger.debug(f"Listed direct aggregates for {table}: {direct_aggs}")

            # Display aggregate sources if this table is itself an aggregate
            for other_table in agg_chain:
                if other_table != table:  # Skip self
                    # Check if this table is a direct or indirect aggregate of other_table
                    if table in agg_chain[other_table].get('direct', []):
                        sourced_directly_label = get_string("report.sections.sourced_directly_from",
                                                           "Sourced Directly From")

                        content.append(f"**{sourced_directly_label}:** `{other_table}`\n")
                        logger.debug(f"{table} is sourced directly from {other_table}")
                    elif table in agg_chain[other_table].get('indirect', []):
                        # Find immediate source
                        immediate_source = None
                        if dependency_graph:
                            # Check each direct aggregate of other_table
                            for direct_agg in agg_chain[other_table].get('direct', []):
                                if table in dependency_graph.get(direct_agg, []):
                                    immediate_source = direct_agg
                                    break

                        # If found, mention the path
                        if immediate_source:
                            sourced_from_label = get_string("report.sections.sourced_from",
                                                           "Sourced From")
                            via_text = get_string("report.sections.via", "via")

                            content.append(f"**{sourced_from_label}:** `{other_table}` {via_text} `{immediate_source}`\n")
                            logger.debug(f"{table} is sourced from {other_table} via {immediate_source}")
                        else:
                            sourced_indirectly_label = get_string("report.sections.sourced_indirectly_from",
                                                                 "Sourced Indirectly From")

                            content.append(f"**{sourced_indirectly_label}:** `{other_table}`\n")
                            logger.debug(f"{table} is sourced indirectly from {other_table}")

        # Schema information
        schema_label = get_string("report.sections.schema", "Schema")
        content.append(f"#### {schema_label}\n")

        schema_headers = get_string("report.table_headers.schema_headers",
                                   ["Column", "Type", "Nullable", "Purpose"])
        schema_rows = []

        for col in schema:
            # Add a descriptive hint for the column
            purpose = get_column_purpose(table, col['name'], col['type'])

            schema_rows.append([
                col['name'],
                col['type'],
                col['nullable'],
                purpose
            ])

        content.append(format_markdown_table(schema_headers, schema_rows))
        content.append("")

        # Index information
        if indexes:
            indexes_label = get_string("report.sections.indexes", "Indexes")
            content.append(f"\n#### {indexes_label}\n")

            idx_headers = get_string("report.table_headers.index_headers",
                                    ["Name", "Columns", "Type", "Purpose"])
            idx_rows = []

            # Get index type labels
            primary_key_text = get_string("report.values.primary_key", "PRIMARY KEY")
            unique_text = get_string("report.values.unique", "UNIQUE")
            index_text = get_string("report.values.index", "INDEX")

            for idx_name, idx_info in indexes.items():
                idx_type = primary_key_text if idx_info['is_primary'] else unique_text if idx_info['is_unique'] else index_text
                columns = ", ".join(idx_info['columns'])

                # Infer purpose of the index using helper function
                purpose = get_index_purpose(idx_name, columns, idx_info['is_primary'],
                                          idx_info['is_unique'], table)

                idx_rows.append([idx_name, columns, idx_type, purpose])

            content.append(format_markdown_table(idx_headers, idx_rows))
            content.append("")

        content.append("\n---\n")

    # Write the report
    with open(output_file, 'w') as f:
        f.write('\n'.join(content))

    logger.info(get_string("log_messages.report_written",
                          "Report written to {file}",
                          file=output_file))
    return True
