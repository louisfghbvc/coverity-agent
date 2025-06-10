"""
Tests for data structures (ParsedDefect and ParsingStatistics).
"""

import json
import pytest
from datetime import datetime
from dataclasses import FrozenInstanceError

import sys
sys.path.insert(0, 'src')

from issue_parser import ParsedDefect, ParsingStatistics


class TestParsedDefect:
    """Test cases for ParsedDefect dataclass."""
    
    def test_from_coverity_tool_output_success(self, formatted_issue_sample):
        """Test successful creation from CoverityReportTool output."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        
        assert defect.defect_type == "AUTO_CAUSES_COPY"
        assert defect.file_path == "/path/to/source.h"
        assert defect.line_number == 230
        assert defect.function_name == "auto testFunction()"
        assert defect.events == [
            "This lambda has an unspecified return type",
            "This return statement creates a copy"
        ]
        assert defect.subcategory == "Using the auto keyword without an & causes a copy."
        assert defect.confidence_score == 1.0
        assert defect.defect_id != ""
        assert len(defect.defect_id) == 8
        assert isinstance(defect.parsing_timestamp, datetime)
        assert defect.raw_data == formatted_issue_sample
    
    def test_from_coverity_tool_output_missing_type(self):
        """Test error handling for missing type field."""
        issue = {
            "mainEventFilepath": "/path/to/file.cpp",
            "mainEventLineNumber": 100,
            "functionDisplayName": "func()",
            "events": {"eventDescription": [], "subcategoryLongDescription": ""}
        }
        
        with pytest.raises(ValueError, match="Missing required field: type"):
            ParsedDefect.from_coverity_tool_output(issue)
    
    def test_from_coverity_tool_output_missing_filepath(self):
        """Test error handling for missing filepath."""
        issue = {
            "type": "TEST_CHECKER",
            "mainEventLineNumber": 100,
            "functionDisplayName": "func()",
            "events": {"eventDescription": [], "subcategoryLongDescription": ""}
        }
        
        with pytest.raises(ValueError, match="Missing required field: mainEventFilepath"):
            ParsedDefect.from_coverity_tool_output(issue)
    
    def test_from_coverity_tool_output_invalid_line_number(self):
        """Test error handling for invalid line number."""
        issue = {
            "type": "TEST_CHECKER",
            "mainEventFilepath": "/path/to/file.cpp",
            "mainEventLineNumber": "not_a_number",
            "functionDisplayName": "func()",
            "events": {"eventDescription": [], "subcategoryLongDescription": ""}
        }
        
        with pytest.raises(ValueError, match="Invalid line number"):
            ParsedDefect.from_coverity_tool_output(issue)
    
    def test_from_coverity_tool_output_events_handling(self):
        """Test various event description formats."""
        # Test with single string event
        issue = {
            "type": "TEST_CHECKER",
            "mainEventFilepath": "/path/to/file.cpp",
            "mainEventLineNumber": 100,
            "functionDisplayName": "func()",
            "events": {"eventDescription": "single event", "subcategoryLongDescription": "test"}
        }
        
        defect = ParsedDefect.from_coverity_tool_output(issue)
        assert defect.events == ["single event"]
        
        # Test with empty events
        issue["events"]["eventDescription"] = []
        defect = ParsedDefect.from_coverity_tool_output(issue)
        assert defect.events == []
    
    def test_validate_success(self, formatted_issue_sample):
        """Test successful validation."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        assert defect.validate() is True
    
    def test_validate_invalid_defect_type(self, formatted_issue_sample):
        """Test validation failure for invalid defect type."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        defect.defect_type = ""
        assert defect.validate() is False
        
        defect.defect_type = 123
        assert defect.validate() is False
    
    def test_validate_invalid_file_path(self, formatted_issue_sample):
        """Test validation failure for invalid file path."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        defect.file_path = ""
        assert defect.validate() is False
        
        defect.file_path = None
        assert defect.validate() is False
    
    def test_validate_invalid_line_number(self, formatted_issue_sample):
        """Test validation failure for invalid line number."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        defect.line_number = 0
        assert defect.validate() is False
        
        defect.line_number = -5
        assert defect.validate() is False
        
        defect.line_number = "not_a_number"
        assert defect.validate() is False
    
    def test_validate_invalid_events(self, formatted_issue_sample):
        """Test validation failure for invalid events."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        defect.events = "not_a_list"
        assert defect.validate() is False
        
        defect.events = [123, "valid_string"]
        assert defect.validate() is False
    
    def test_validate_invalid_confidence_score(self, formatted_issue_sample):
        """Test validation failure for invalid confidence score."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        defect.confidence_score = 1.5  # > 1.0
        assert defect.validate() is False
        
        defect.confidence_score = -0.1  # < 0.0
        assert defect.validate() is False
        
        defect.confidence_score = "not_a_number"
        assert defect.validate() is False
    
    def test_to_dict(self, formatted_issue_sample):
        """Test dictionary serialization."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        result = defect.to_dict()
        
        assert isinstance(result, dict)
        assert result["defect_type"] == "AUTO_CAUSES_COPY"
        assert result["file_path"] == "/path/to/source.h"
        assert result["line_number"] == 230
        assert result["function_name"] == "auto testFunction()"
        assert result["events"] == defect.events
        assert result["subcategory"] == defect.subcategory
        assert result["confidence_score"] == 1.0
        assert result["defect_id"] == defect.defect_id
        assert "parsing_timestamp" in result
        assert "raw_data" in result
    
    def test_from_dict(self, formatted_issue_sample):
        """Test creation from dictionary."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        defect_dict = defect.to_dict()
        
        restored_defect = ParsedDefect.from_dict(defect_dict)
        
        assert restored_defect.defect_type == defect.defect_type
        assert restored_defect.file_path == defect.file_path
        assert restored_defect.line_number == defect.line_number
        assert restored_defect.function_name == defect.function_name
        assert restored_defect.events == defect.events
        assert restored_defect.subcategory == defect.subcategory
        assert restored_defect.confidence_score == defect.confidence_score
        assert restored_defect.defect_id == defect.defect_id
    
    def test_json_serialization(self, formatted_issue_sample):
        """Test JSON serialization and deserialization."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        
        # Test to_json
        json_str = defect.to_json()
        assert isinstance(json_str, str)
        assert "AUTO_CAUSES_COPY" in json_str
        
        # Verify it's valid JSON
        json_data = json.loads(json_str)
        assert isinstance(json_data, dict)
        
        # Test from_json
        restored_defect = ParsedDefect.from_json(json_str)
        assert restored_defect.defect_type == defect.defect_type
        assert restored_defect.file_path == defect.file_path
        assert restored_defect.line_number == defect.line_number
    
    def test_string_representations(self, formatted_issue_sample):
        """Test __str__ and __repr__ methods."""
        defect = ParsedDefect.from_coverity_tool_output(formatted_issue_sample)
        
        str_repr = str(defect)
        assert "ParsedDefect" in str_repr
        assert "AUTO_CAUSES_COPY" in str_repr
        assert "/path/to/source.h:230" in str_repr
        
        repr_str = repr(defect)
        assert "ParsedDefect" in repr_str
        assert "defect_id=" in repr_str
        assert "defect_type=" in repr_str
    
    def test_default_values(self):
        """Test default field values."""
        defect = ParsedDefect(
            defect_type="TEST",
            file_path="/test.cpp",
            line_number=1,
            function_name="test()",
            events=["test event"],
            subcategory="test"
        )
        
        assert len(defect.defect_id) == 8
        assert defect.confidence_score == 1.0
        assert isinstance(defect.parsing_timestamp, datetime)
        assert defect.raw_data is None


class TestParsingStatistics:
    """Test cases for ParsingStatistics dataclass."""
    
    def test_default_values(self):
        """Test default field values."""
        stats = ParsingStatistics()
        
        assert stats.total_issues_found == 0
        assert stats.issues_processed == 0
        assert stats.issues_skipped == 0
        assert stats.issues_excluded == 0
        assert stats.parsing_errors == 0
        assert stats.categories_found == []
        assert stats.processing_time_seconds == 0.0
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        stats = ParsingStatistics(
            total_issues_found=100,
            issues_processed=85,
            issues_skipped=10,
            issues_excluded=5,
            parsing_errors=2,
            categories_found=["TEST_CHECKER", "AUTO_CAUSES_COPY"],
            processing_time_seconds=1.5
        )
        
        result = stats.to_dict()
        
        assert isinstance(result, dict)
        assert result["total_issues_found"] == 100
        assert result["issues_processed"] == 85
        assert result["issues_skipped"] == 10
        assert result["issues_excluded"] == 5
        assert result["parsing_errors"] == 2
        assert result["categories_found"] == ["TEST_CHECKER", "AUTO_CAUSES_COPY"]
        assert result["processing_time_seconds"] == 1.5
    
    def test_categories_list_independence(self):
        """Test that categories_found list is independent."""
        stats = ParsingStatistics()
        original_categories = stats.categories_found
        
        # Modify the returned list from to_dict
        result_dict = stats.to_dict()
        result_dict["categories_found"].append("NEW_CATEGORY")
        
        # Original should be unchanged
        assert stats.categories_found == original_categories
        assert "NEW_CATEGORY" not in stats.categories_found 