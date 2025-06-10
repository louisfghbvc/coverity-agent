"""
Issue Parser Package

This package provides tools for parsing and analyzing Coverity static analysis reports.
It includes:
- CoverityReportTool: Core analysis functionality
- CoverityPipelineAdapter: Pipeline integration adapter
- ParsedDefect: Pipeline-compatible data structure
- Exception classes for error handling

Extracted from proven MCP server implementation and adapted for pipeline usage.
"""

from .coverity_tool import CoverityReportTool
from .adapter import CoverityPipelineAdapter
from .data_structures import ParsedDefect, ParsingStatistics
from .exceptions import CoverityError, ReportNotFoundError, InvalidReportError

__all__ = [
    'CoverityReportTool',
    'CoverityPipelineAdapter',
    'ParsedDefect',
    'ParsingStatistics',
    'CoverityError',
    'ReportNotFoundError',
    'InvalidReportError'
]

__version__ = '1.0.0' 