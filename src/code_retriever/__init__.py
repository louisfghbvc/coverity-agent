"""
Code Retriever Module

This module provides source code context extraction capabilities for the
Coverity Agent pipeline. It extracts relevant source code context around
defects for consumption by the LLM Fix Generator.

Main Components:
- ContextAnalyzer: Main analyzer for extracting code context
- SourceFileManager: File reading and encoding detection
- LanguageParser: Language detection and parsing
- CodeContext: Output data structure for LLM consumption

Example Usage:
    from src.code_retriever import ContextAnalyzer, CodeRetrieverConfig
    from src.issue_parser.data_structures import ParsedDefect
    
    # Initialize analyzer
    config = CodeRetrieverConfig()
    analyzer = ContextAnalyzer(config)
    
    # Extract context for a defect
    context = analyzer.extract_context(parsed_defect)
    
    # Use context with LLM Fix Generator
    # llm_generator.generate_fix(context)
"""

# Main classes - public API
from .context_analyzer import ContextAnalyzer, extract_code_context
from .source_file_manager import SourceFileManager
from .language_parser import LanguageParser
from .config import CodeRetrieverConfig, ContextWindowConfig

# Data structures
from .data_structures import (
    CodeContext,
    SourceLocation,
    ContextWindow,
    FunctionContext,
    FileMetadata,
    ExtractionStatistics
)

# Exceptions
from .exceptions import (
    CodeRetrieverError,
    FileAccessError,
    EncodingDetectionError,
    LanguageDetectionError,
    ContextExtractionError,
    ParsingError,
    ConfigurationError
)

# Version information
__version__ = "1.0.0"
__author__ = "Coverity Agent Team"

# Public API exports
__all__ = [
    # Main classes
    "ContextAnalyzer",
    "SourceFileManager", 
    "LanguageParser",
    "CodeRetrieverConfig",
    "ContextWindowConfig",
    
    # Data structures
    "CodeContext",
    "SourceLocation",
    "ContextWindow", 
    "FunctionContext",
    "FileMetadata",
    "ExtractionStatistics",
    
    # Exceptions
    "CodeRetrieverError",
    "FileAccessError",
    "EncodingDetectionError",
    "LanguageDetectionError",
    "ContextExtractionError",
    "ParsingError",
    "ConfigurationError",
    
    # Convenience functions
    "extract_code_context"
] 