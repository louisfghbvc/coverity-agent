---
id: 3
title: 'Create ParsedDefect Dataclass'
status: pending
priority: high
feature: Issue Parser
dependencies:
  - 1
assigned_agent: null
created_at: "2025-06-10T05:39:44Z"
started_at: null
completed_at: null
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