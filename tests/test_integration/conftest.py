"""
Pytest configuration for integration tests.
"""

import pytest
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


@pytest.fixture(scope="session")
def real_coverity_report_path():
    """Path to real Coverity report for integration testing."""
    return "/home/scratch.louiliu_vlsi_1/work/nvtools_louiliu_2/nvtools/cad/cadlib/vector/coverity/libvector.so/report.json"


@pytest.fixture(scope="session")
def sample_coverity_report_path():
    """Path to sample Coverity report for testing."""
    test_dir = Path(__file__).parent.parent
    return str(test_dir / "test_issue_parser" / "fixtures" / "sample_report.json")


@pytest.fixture(scope="session")
def project_root():
    """Path to project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def integration_test_config():
    """Configuration for integration tests."""
    return {
        "max_defects_to_test": 5,
        "min_success_rate": 0.5,
        "timeout_seconds": 30
    } 