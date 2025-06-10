---
id: 3
title: 'Create ParsedDefect Dataclass'
status: completed
priority: high
feature: Issue Parser
dependencies:
  - 1
assigned_agent: null
created_at: "2025-06-10T05:39:44Z"
started_at: "2025-06-10T06:13:50Z"
completed_at: "2025-06-10T06:19:57Z"
error_log: null
---

## Description

Design pipeline-compatible data structure for standardized defect representation

## Details

- Create `ParsedDefect` dataclass in `src/issue_parser/data_structures.py`
- Design as bridge between existing CoverityReportTool output and pipeline requirements
- Core fields mapping from existing `format_issue_for_query()` output:
  - `defect_type: str` (from "type")
  - `file_path: str` (from "mainEventFilepath") 
  - `line_number: int` (from "mainEventLineNumber")
  - `function_name: str` (from "functionDisplayName")
  - `events: List[str]` (from "events.eventDescription")
  - `subcategory: str` (from "events.subcategoryLongDescription")
- Additional pipeline fields:
  - `defect_id: str = ""` (generated identifier)
  - `confidence_score: float = 1.0` (parsing confidence)
  - `parsing_timestamp: datetime = None` (when parsed)
  - `raw_data: Dict[str, Any] = None` (original data)
- Implement class method: `from_coverity_tool_output(cls, formatted_issue: Dict[str, Any]) -> 'ParsedDefect'`
- Add validation methods for required fields
- Include JSON serialization/deserialization support
- Add string representation for debugging
- Complete implementation:
  ```python
  @dataclass
  class ParsedDefect:
      # Core fields + Additional pipeline fields
      
      @classmethod
      def from_coverity_tool_output(cls, formatted_issue: Dict[str, Any]) -> 'ParsedDefect':
          # Convert from existing tool format
          
      def validate(self) -> bool:
          # Validate required fields
          
      def to_dict(self) -> Dict[str, Any]:
          # JSON serialization
  ```

## Test Strategy

- Test ParsedDefect creation from existing tool output format
- Verify all field mappings are correct
- Test validation method with valid and invalid data
- Confirm JSON serialization/deserialization works
- Test edge cases (missing fields, empty values)
- Validate dataclass immutability and type hints

## Agent Notes

**✅ COMPLETED AS PART OF TASK 2**

**Implementation Summary:**
- ParsedDefect dataclass implemented in `src/issue_parser/data_structures.py` as part of Task 2 execution
- Created comprehensive data structure that perfectly bridges CoverityReportTool output with pipeline requirements
- Includes both core defect fields and additional pipeline metadata

**Files Created:**
- `src/issue_parser/data_structures.py` - Contains ParsedDefect and ParsingStatistics dataclasses

**ParsedDefect Features Implemented ✅:**
- **Core Field Mapping**: Exact mapping from CoverityReportTool.format_issue_for_query() output
  - `defect_type` ← "type"
  - `file_path` ← "mainEventFilepath"  
  - `line_number` ← "mainEventLineNumber"
  - `function_name` ← "functionDisplayName"
  - `events` ← "events.eventDescription" (list)
  - `subcategory` ← "events.subcategoryLongDescription"

- **Pipeline Enhancement Fields**:
  - `defect_id`: Auto-generated UUID (8 chars)
  - `confidence_score`: Float 0.0-1.0 (defaults to 1.0)
  - `parsing_timestamp`: UTC datetime of parsing
  - `raw_data`: Original formatted issue data for reference

- **Class Methods**:
  - `from_coverity_tool_output()`: Seamless conversion from existing tool
  - `from_dict()` / `to_dict()`: Dictionary serialization
  - `from_json()` / `to_json()`: JSON serialization
  - `validate()`: Comprehensive field validation

- **Error Handling**: Proper ValueError exceptions for missing required fields
- **String Representations**: Both `__str__()` and `__repr__()` for debugging
- **Type Safety**: Full type hints with dataclass decorators

**Additional Component - ParsingStatistics:**
- Statistics dataclass for monitoring adapter operations
- Tracks: total_issues_found, issues_processed, issues_skipped, issues_excluded, parsing_errors, categories_found, processing_time_seconds

**Testing Verification:**
- ParsedDefect creation from tool output ✅
- Field mapping accuracy ✅  
- Validation with valid/invalid data ✅
- JSON serialization/deserialization ✅
- Edge cases and error handling ✅
- Type hint compliance ✅

**Integration Success:**
- Seamlessly integrates with CoverityPipelineAdapter
- Zero data loss in conversion process
- Maintains all original defect information plus pipeline metadata
- Ready for downstream pipeline components 