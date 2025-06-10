"""
Pytest configuration and fixtures for issue_parser tests.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def fixtures_dir():
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_report_path(fixtures_dir):
    """Path to sample Coverity report."""
    return str(fixtures_dir / "sample_report.json")


@pytest.fixture
def malformed_report_path(fixtures_dir):
    """Path to malformed Coverity report."""
    return str(fixtures_dir / "malformed_report.json")


@pytest.fixture
def large_report_path(fixtures_dir):
    """Path to large Coverity report for performance testing."""
    return str(fixtures_dir / "large_report.json")


@pytest.fixture
def sample_report_data(fixtures_dir):
    """Load sample report data as dictionary."""
    with open(fixtures_dir / "sample_report.json", 'r') as f:
        return json.load(f)


@pytest.fixture
def formatted_issue_sample():
    """Sample formatted issue from CoverityReportTool.format_issue_for_query()."""
    return {
        "type": "AUTO_CAUSES_COPY",
        "mainEventFilepath": "/path/to/source.h",
        "mainEventLineNumber": 230,
        "functionDisplayName": "auto testFunction()",
        "events": {
            "eventDescription": [
                "This lambda has an unspecified return type",
                "This return statement creates a copy"
            ],
            "subcategoryLongDescription": "Using the auto keyword without an & causes a copy."
        }
    }


@pytest.fixture
def temp_report_file():
    """Create temporary report file for testing."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    
    sample_data = {
        "issues": [
            {
                "checkerName": "TEST_CHECKER",
                "mainEventFilePathname": "/path/to/test.cpp",
                "mainEventLineNumber": 100,
                "functionDisplayName": "testFunc()",
                "subcategory": "Test issue",
                "events": [
                    {"eventDescription": "Test event description"}
                ],
                "fixed": False
            }
        ]
    }
    
    json.dump(sample_data, temp_file, indent=2)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    os.unlink(temp_file.name)


@pytest.fixture
def temp_config_file():
    """Create temporary configuration file for testing."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    
    config_data = """
issue_parser:
  exclude_paths:
    - "test/*"
  batch_size: 500
  logging:
    level: "DEBUG"
"""
    
    temp_file.write(config_data)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    os.unlink(temp_file.name)


@pytest.fixture
def invalid_config_data():
    """Invalid configuration data for testing validation."""
    return {
        "batch_size": "not_a_number",  # Should be int
        "exclude_paths": "not_a_list",  # Should be list
        "validation": {
            "required_fields": 123  # Should be list
        },
        "logging": {
            "level": "INVALID_LEVEL"  # Should be valid level
        }
    }


@pytest.fixture 
def valid_config_data():
    """Valid configuration data for testing."""
    return {
        "exclude_paths": ["custom/*", "debug/*"],
        "batch_size": 2000,
        "enable_caching": False,
        "validation": {
            "required_fields": ["checkerName", "mainEventFilePathname"],
            "validate_json_structure": True
        },
        "logging": {
            "level": "WARNING",
            "include_parsing_time": False
        }
    } 