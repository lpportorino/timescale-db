"""
String handling module for TimescaleDB Report Generator.

This module handles loading and accessing strings from the TOML configuration file.
"""

import os
import logging
import toml
from pathlib import Path

# Global configuration dictionary
_config = None

def get_config():
    """Get the configuration object, loading it if not already loaded.

    Returns:
        dict: The configuration dictionary from the TOML file
    """
    global _config
    if _config is None:
        load_config()
    return _config

def load_config(config_path=None):
    """Load the configuration from the TOML file.

    Args:
        config_path (str, optional): Path to the TOML config file.
            If None, will look in default locations.

    Returns:
        dict: The loaded configuration
    """
    global _config

    # Default paths to search for the config
    search_paths = [
        # Current directory
        Path("timescaledb_report_strings.toml"),
        # Alongside the package
        Path(__file__).parent / "timescaledb_report_strings.toml",
        # In user config directory
        Path(os.path.expanduser("~/.config/timescaledb_report/strings.toml")),
        # System-wide config
        Path("/etc/timescaledb_report/strings.toml")
    ]

    # If a specific path is provided, try that first
    if config_path:
        try:
            _config = toml.load(config_path)
            return _config
        except Exception as e:
            logging.warning(f"Failed to load config from {config_path}: {e}")
            # Continue to try default paths

    # Try each path in order
    for path in search_paths:
        if path.exists():
            try:
                _config = toml.load(str(path))
                return _config
            except Exception as e:
                logging.warning(f"Failed to load config from {path}: {e}")

    # If we get here, we couldn't load the config
    logging.warning("Could not find or load strings configuration. Using defaults.")
    # Initialize with an empty dict to avoid further load attempts
    _config = {}
    return _config

def get_string(path, default=None, **format_args):
    """Get a string from the configuration with formatting.

    Args:
        path (str): Dot-separated path to the string in the config
        default (str, optional): Default value if path not found
        **format_args: Arguments to format the string with

    Returns:
        str: The formatted string, or default if not found
    """
    config = get_config()

    # Navigate the config dictionary using the path
    parts = path.split('.')
    value = config
    for part in parts:
        if part in value:
            value = value[part]
        else:
            return default if default is not None else path

    # Format the string if format args are provided
    if isinstance(value, str) and format_args:
        try:
            return value.format(**format_args)
        except KeyError as e:
            logging.warning(f"Missing format argument {e} for string {path}")
            return value

    return value
