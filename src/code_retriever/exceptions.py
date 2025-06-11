"""
Code Retriever specific exceptions.

This module defines exceptions specific to the Code Retriever component,
following the structured exception hierarchy pattern.
"""


class CodeRetrieverError(Exception):
    """Base exception for Code Retriever component."""
    pass


class FileAccessError(CodeRetrieverError):
    """Raised when unable to access or read source files."""
    pass


class EncodingDetectionError(CodeRetrieverError):
    """Raised when unable to detect file encoding."""
    pass


class LanguageDetectionError(CodeRetrieverError):
    """Raised when unable to detect source code language."""
    pass


class ContextExtractionError(CodeRetrieverError):
    """Raised when unable to extract context around defect location."""
    pass


class ParsingError(CodeRetrieverError):
    """Raised when unable to parse source code structure."""
    pass


class ConfigurationError(CodeRetrieverError):
    """Raised when Code Retriever configuration is invalid."""
    pass 