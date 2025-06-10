"""
Coverity Report Tool Exceptions

Exception classes for the Coverity report analysis tool.
"""


class CoverityError(Exception):
    """Base exception for Coverity tool errors."""
    pass


class ReportNotFoundError(CoverityError):
    """Exception raised when report file is not found."""
    pass


class InvalidReportError(CoverityError):
    """Exception raised when report file is invalid."""
    pass 