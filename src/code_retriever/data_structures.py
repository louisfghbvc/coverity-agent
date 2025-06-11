"""
Data Structures for Code Retriever

This module defines data structures for representing extracted source code context
around defects. These structures are used to pass information from Code Retriever
to LLM Fix Generator.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class SourceLocation:
    """Represents a specific location in source code."""
    
    file_path: str
    line_number: int
    column_number: int = 0
    function_name: str = ""
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.function_name:
            return f"{self.file_path}:{self.line_number}:{self.column_number} in {self.function_name}()"
        return f"{self.file_path}:{self.line_number}:{self.column_number}"


@dataclass
class ContextWindow:
    """Represents a window of source code context around a location."""
    
    start_line: int
    end_line: int
    source_lines: List[str]
    highlighted_line: Optional[int] = None  # Line within window that contains the defect
    
    def get_line_count(self) -> int:
        """Get the number of lines in this context window."""
        return len(self.source_lines)
    
    def get_highlighted_line_content(self) -> Optional[str]:
        """Get the content of the highlighted line if it exists."""
        if self.highlighted_line is not None and 0 <= self.highlighted_line < len(self.source_lines):
            return self.source_lines[self.highlighted_line]
        return None


@dataclass
class FunctionContext:
    """Represents context information about a function containing a defect."""
    
    name: str
    start_line: int
    end_line: int
    parameters: List[str] = field(default_factory=list)
    return_type: str = ""
    signature: str = ""
    is_complete: bool = True  # False if function extends beyond extracted context
    
    def get_line_count(self) -> int:
        """Get the number of lines in this function."""
        return self.end_line - self.start_line + 1


@dataclass
class FileMetadata:
    """Metadata about a source file."""
    
    file_path: str
    file_size: int
    encoding: str
    language: str
    last_modified: Optional[datetime] = None
    
    @classmethod
    def from_path(cls, file_path: Path, encoding: str, language: str) -> 'FileMetadata':
        """Create FileMetadata from a file path."""
        try:
            stat = file_path.stat()
            return cls(
                file_path=str(file_path),
                file_size=stat.st_size,
                encoding=encoding,
                language=language,
                last_modified=datetime.fromtimestamp(stat.st_mtime)
            )
        except (OSError, ValueError):
            return cls(
                file_path=str(file_path),
                file_size=0,
                encoding=encoding,
                language=language
            )


@dataclass
class CodeContext:
    """Complete code context around a defect for LLM processing.
    
    This is the primary output data structure from Code Retriever,
    containing all necessary context for LLM Fix Generator.
    """
    
    # Core identification
    defect_id: str
    defect_type: str
    
    # Primary location and context
    primary_location: SourceLocation
    primary_context: ContextWindow
    file_metadata: FileMetadata
    
    # Function context (if defect is within a function)
    function_context: Optional[FunctionContext] = None
    
    # Additional context files/locations
    related_locations: List[Tuple[SourceLocation, ContextWindow]] = field(default_factory=list)
    
    # Language-specific information
    language: str = "unknown"
    syntax_elements: Dict[str, Any] = field(default_factory=dict)
    
    # Classification hints from Issue Parser
    classification_hints: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    
    # Processing metadata
    extraction_timestamp: datetime = field(default_factory=datetime.utcnow)
    context_size_lines: int = 0
    
    def __post_init__(self):
        """Post-initialization processing."""
        self.context_size_lines = self.primary_context.get_line_count()
        if self.related_locations:
            self.context_size_lines += sum(ctx.get_line_count() for _, ctx in self.related_locations)
    
    @classmethod
    def from_parsed_defect(cls, parsed_defect, primary_location: SourceLocation, 
                          primary_context: ContextWindow, file_metadata: FileMetadata) -> 'CodeContext':
        """Create CodeContext from a ParsedDefect object.
        
        Args:
            parsed_defect: ParsedDefect instance from Issue Parser
            primary_location: Main defect location
            primary_context: Source code context around defect
            file_metadata: Metadata about the source file
            
        Returns:
            CodeContext instance
        """
        # Extract classification hints from ParsedDefect
        classification_hints = {
            "defect_type": parsed_defect.defect_type,
            "subcategory": parsed_defect.subcategory,
            "events": parsed_defect.events.copy(),
            "function_name": parsed_defect.function_name
        }
        
        # Add raw data if available
        if parsed_defect.raw_data:
            classification_hints["raw_data"] = parsed_defect.raw_data.copy()
        
        return cls(
            defect_id=parsed_defect.defect_id,
            defect_type=parsed_defect.defect_type,
            primary_location=primary_location,
            primary_context=primary_context,
            file_metadata=file_metadata,
            classification_hints=classification_hints,
            confidence_score=parsed_defect.confidence_score
        )
    
    def add_related_context(self, location: SourceLocation, context: ContextWindow):
        """Add additional context from related locations."""
        self.related_locations.append((location, context))
        self.context_size_lines += context.get_line_count()
    
    def set_function_context(self, function_context: FunctionContext):
        """Set the function context for this defect."""
        self.function_context = function_context
    
    def get_total_context_lines(self) -> int:
        """Get the total number of lines in all context windows."""
        return self.context_size_lines
    
    def get_all_source_lines(self) -> List[str]:
        """Get all source lines from primary and related contexts."""
        all_lines = self.primary_context.source_lines.copy()
        for _, context in self.related_locations:
            all_lines.extend(context.source_lines)
        return all_lines
    
    def validate(self) -> bool:
        """Validate that the CodeContext has all required fields and valid data.
        
        Returns:
            True if valid, False otherwise
        """
        # Check required string fields
        if not self.defect_id or not isinstance(self.defect_id, str):
            return False
        if not self.defect_type or not isinstance(self.defect_type, str):
            return False
        if not self.language or not isinstance(self.language, str):
            return False
            
        # Check primary location
        if not isinstance(self.primary_location, SourceLocation):
            return False
        if not self.primary_location.file_path or self.primary_location.line_number <= 0:
            return False
            
        # Check primary context
        if not isinstance(self.primary_context, ContextWindow):
            return False
        if not self.primary_context.source_lines or self.primary_context.start_line <= 0:
            return False
            
        # Check file metadata
        if not isinstance(self.file_metadata, FileMetadata):
            return False
        if not self.file_metadata.file_path or not self.file_metadata.encoding:
            return False
            
        # Check confidence score
        if not isinstance(self.confidence_score, (int, float)) or not (0.0 <= self.confidence_score <= 1.0):
            return False
            
        # Check related locations if present
        for location, context in self.related_locations:
            if not isinstance(location, SourceLocation) or not isinstance(context, ContextWindow):
                return False
                
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert CodeContext to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        result = {
            "defect_id": self.defect_id,
            "defect_type": self.defect_type,
            "primary_location": {
                "file_path": self.primary_location.file_path,
                "line_number": self.primary_location.line_number,
                "column_number": self.primary_location.column_number,
                "function_name": self.primary_location.function_name
            },
            "primary_context": {
                "start_line": self.primary_context.start_line,
                "end_line": self.primary_context.end_line,
                "source_lines": self.primary_context.source_lines.copy(),
                "highlighted_line": self.primary_context.highlighted_line
            },
            "file_metadata": {
                "file_path": self.file_metadata.file_path,
                "file_size": self.file_metadata.file_size,
                "encoding": self.file_metadata.encoding,
                "language": self.file_metadata.language,
                "last_modified": self.file_metadata.last_modified.isoformat() if self.file_metadata.last_modified else None
            },
            "language": self.language,
            "syntax_elements": self.syntax_elements.copy(),
            "classification_hints": self.classification_hints.copy(),
            "confidence_score": self.confidence_score,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "context_size_lines": self.context_size_lines
        }
        
        # Add function context if present
        if self.function_context:
            result["function_context"] = {
                "name": self.function_context.name,
                "start_line": self.function_context.start_line,
                "end_line": self.function_context.end_line,
                "parameters": self.function_context.parameters.copy(),
                "return_type": self.function_context.return_type,
                "signature": self.function_context.signature,
                "is_complete": self.function_context.is_complete
            }
        
        # Add related locations if present
        if self.related_locations:
            result["related_locations"] = []
            for location, context in self.related_locations:
                result["related_locations"].append({
                    "location": {
                        "file_path": location.file_path,
                        "line_number": location.line_number,
                        "column_number": location.column_number,
                        "function_name": location.function_name
                    },
                    "context": {
                        "start_line": context.start_line,
                        "end_line": context.end_line,
                        "source_lines": context.source_lines.copy(),
                        "highlighted_line": context.highlighted_line
                    }
                })
        
        return result
    
    def to_json(self) -> str:
        """Convert CodeContext to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    def __str__(self) -> str:
        """Human-readable string representation for debugging."""
        func_info = f" in {self.function_context.name}()" if self.function_context else ""
        return (f"CodeContext(id={self.defect_id}, type={self.defect_type}, "
                f"location={self.primary_location.file_path}:{self.primary_location.line_number}"
                f"{func_info}, lines={self.context_size_lines})")
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (f"CodeContext(defect_id='{self.defect_id}', defect_type='{self.defect_type}', "
                f"file='{self.primary_location.file_path}', lines={self.context_size_lines})")


@dataclass
class ExtractionStatistics:
    """Statistics from code context extraction operations."""
    
    defects_processed: int = 0
    contexts_extracted: int = 0
    extraction_errors: int = 0
    files_accessed: int = 0
    total_context_lines: int = 0
    processing_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "defects_processed": self.defects_processed,
            "contexts_extracted": self.contexts_extracted,
            "extraction_errors": self.extraction_errors,
            "files_accessed": self.files_accessed,
            "total_context_lines": self.total_context_lines,
            "processing_time_seconds": self.processing_time_seconds
        } 