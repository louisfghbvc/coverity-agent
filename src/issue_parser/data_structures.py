"""
Data Structures for Issue Parser

This module defines pipeline-compatible data structures for representing
parsed Coverity defects. The structures bridge between the CoverityReportTool
output format and standardized pipeline requirements.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class ParsedDefect:
    """Pipeline-compatible representation of a Coverity defect.
    
    This dataclass bridges between the CoverityReportTool output format
    and the standardized pipeline data structures. It includes both core
    defect information and additional metadata for pipeline processing.
    """
    
    # Core fields mapped from CoverityReportTool.format_issue_for_query() output
    defect_type: str                    # from "type" 
    file_path: str                      # from "mainEventFilepath"
    line_number: int                    # from "mainEventLineNumber"
    function_name: str                  # from "functionDisplayName"
    events: List[str]                   # from "events.eventDescription"
    subcategory: str                    # from "events.subcategoryLongDescription"
    
    # Additional pipeline fields
    defect_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    confidence_score: float = 1.0
    parsing_timestamp: Optional[datetime] = field(default_factory=datetime.utcnow)
    raw_data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_coverity_tool_output(cls, formatted_issue: Dict[str, Any]) -> 'ParsedDefect':
        """Create ParsedDefect from CoverityReportTool.format_issue_for_query() output.
        
        Args:
            formatted_issue: Output from CoverityReportTool.format_issue_for_query()
            
        Returns:
            ParsedDefect instance with mapped fields
            
        Raises:
            ValueError: If required fields are missing from input
        """
        # Extract core fields with validation
        defect_type = formatted_issue.get("type", "")
        if not defect_type:
            raise ValueError("Missing required field: type")
            
        file_path = formatted_issue.get("mainEventFilepath", "")
        if not file_path:
            raise ValueError("Missing required field: mainEventFilepath")
            
        line_number = formatted_issue.get("mainEventLineNumber", 0)
        if not isinstance(line_number, int) or line_number <= 0:
            raise ValueError("Invalid line number: must be positive integer")
            
        function_name = formatted_issue.get("functionDisplayName", "")
        
        # Extract events data
        events_data = formatted_issue.get("events", {})
        event_descriptions = events_data.get("eventDescription", [])
        if not isinstance(event_descriptions, list):
            event_descriptions = [str(event_descriptions)] if event_descriptions else []
            
        subcategory = events_data.get("subcategoryLongDescription", "")
        
        return cls(
            defect_type=defect_type,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            events=event_descriptions,
            subcategory=subcategory,
            raw_data=formatted_issue.copy()
        )
    
    def validate(self) -> bool:
        """Validate that the ParsedDefect has all required fields.
        
        Returns:
            True if valid, False otherwise
        """
        # Check required string fields
        if not self.defect_type or not isinstance(self.defect_type, str):
            return False
        if not self.file_path or not isinstance(self.file_path, str):
            return False
        if not isinstance(self.function_name, str):  # Can be empty
            return False
        if not isinstance(self.subcategory, str):  # Can be empty
            return False
            
        # Check line number
        if not isinstance(self.line_number, int) or self.line_number <= 0:
            return False
            
        # Check events list
        if not isinstance(self.events, list):
            return False
        if not all(isinstance(event, str) for event in self.events):
            return False
            
        # Check optional fields have correct types
        if not isinstance(self.defect_id, str):
            return False
        if not isinstance(self.confidence_score, (int, float)) or not (0.0 <= self.confidence_score <= 1.0):
            return False
        if self.parsing_timestamp is not None and not isinstance(self.parsing_timestamp, datetime):
            return False
        if self.raw_data is not None and not isinstance(self.raw_data, dict):
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ParsedDefect to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        result = {
            "defect_id": self.defect_id,
            "defect_type": self.defect_type,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "events": self.events.copy(),
            "subcategory": self.subcategory,
            "confidence_score": self.confidence_score,
            "parsing_timestamp": self.parsing_timestamp.isoformat() if self.parsing_timestamp else None,
        }
        
        # Include raw_data if present (excluding to avoid duplication by default)
        if self.raw_data is not None:
            result["raw_data"] = self.raw_data.copy()
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedDefect':
        """Create ParsedDefect from dictionary (inverse of to_dict).
        
        Args:
            data: Dictionary with ParsedDefect fields
            
        Returns:
            ParsedDefect instance
        """
        # Handle timestamp parsing
        timestamp_str = data.get("parsing_timestamp")
        parsing_timestamp = None
        if timestamp_str:
            try:
                parsing_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                parsing_timestamp = None
                
        return cls(
            defect_id=data.get("defect_id", ""),
            defect_type=data.get("defect_type", ""),
            file_path=data.get("file_path", ""),
            line_number=data.get("line_number", 0),
            function_name=data.get("function_name", ""),
            events=data.get("events", []).copy() if data.get("events") else [],
            subcategory=data.get("subcategory", ""),
            confidence_score=data.get("confidence_score", 1.0),
            parsing_timestamp=parsing_timestamp,
            raw_data=data.get("raw_data", {}).copy() if data.get("raw_data") else None
        )
    
    def to_json(self) -> str:
        """Convert ParsedDefect to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ParsedDefect':
        """Create ParsedDefect from JSON string.
        
        Args:
            json_str: JSON string with ParsedDefect data
            
        Returns:
            ParsedDefect instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """Human-readable string representation for debugging."""
        return (f"ParsedDefect(id={self.defect_id}, type={self.defect_type}, "
                f"file={self.file_path}:{self.line_number}, func={self.function_name})")
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (f"ParsedDefect(defect_id='{self.defect_id}', defect_type='{self.defect_type}', "
                f"file_path='{self.file_path}', line_number={self.line_number})")


@dataclass 
class ParsingStatistics:
    """Statistics from parsing operations for monitoring and debugging."""
    
    total_issues_found: int = 0
    issues_processed: int = 0
    issues_skipped: int = 0
    issues_excluded: int = 0
    parsing_errors: int = 0
    categories_found: List[str] = field(default_factory=list)
    processing_time_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_issues_found": self.total_issues_found,
            "issues_processed": self.issues_processed,
            "issues_skipped": self.issues_skipped,
            "issues_excluded": self.issues_excluded,
            "parsing_errors": self.parsing_errors,
            "categories_found": self.categories_found.copy(),
            "processing_time_seconds": self.processing_time_seconds
        } 