"""
Issue Parser Package

This package provides tools for parsing and analyzing Coverity static analysis reports.
It includes:
- CoverityReportTool: Core analysis functionality
- Exception classes for error handling
- Pipeline integration adapters (future tasks)

Extracted from proven MCP server implementation and adapted for pipeline usage.
"""

from .coverity_tool import CoverityReportTool
from .exceptions import CoverityError, ReportNotFoundError, InvalidReportError

__all__ = [
    'CoverityReportTool',
    'CoverityError',
    'ReportNotFoundError',
    'InvalidReportError'
]

__version__ = '1.0.0' 