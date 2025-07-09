#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="timescaledb-report",
    version="1.2.0",
    description="Generate schema-focused reports for TimescaleDB databases",
    author="Jettison Team",
    packages=find_packages(),
    install_requires=[
        "psycopg2-binary>=2.9.3",
        "tabulate>=0.8.10",
        "PyYAML>=6.0",
        "markdown>=3.3.6",
        "toml>=0.10.2",
    ],
    entry_points={
        'console_scripts': [
            'timescaledb-report=run:main',
        ],
    },
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
