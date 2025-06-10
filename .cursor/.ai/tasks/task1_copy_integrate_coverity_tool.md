---
id: 1
title: 'Copy and Integrate Existing CoverityReportTool'
status: completed
priority: critical
feature: Issue Parser
dependencies: []
assigned_agent: null
created_at: "2025-06-10T05:39:44Z"
started_at: "2025-06-10T05:43:56Z"
completed_at: "2025-06-10T06:09:14Z"
error_log: null
---

## Description

Extract and adapt existing comprehensive Coverity analysis tool for the pipeline architecture

## Details

- Copy the existing CoverityReportTool class from `/home/scratch.louiliu_vlsi_1/sideProject/mcp-coverity/mcp-servers/coverity/coverity.py`
- Create new module structure in `src/issue_parser/`
- Extract core functionality from MCP server wrapper to focus on analysis capabilities
- Preserve all existing features:
  - JSON report loading with validation
  - Issue querying by category with case-insensitive matching  
  - Path exclusion with glob-style patterns
  - Issue grouping by location (file, line, function)
  - Event description extraction
  - Issue summarization by category
  - Auto-fix tracking (marking issues as processed)
- Remove MCP-specific dependencies and async wrapper code
- Ensure all existing exception classes are preserved (CoverityError, ReportNotFoundError, InvalidReportError)
- Create clean module structure:
  ```
  src/issue_parser/
  ├── __init__.py
  ├── coverity_tool.py      # Core CoverityReportTool
  └── exceptions.py         # Exception classes
  ```

## Test Strategy

- Verify the extracted tool can load a Coverity JSON report successfully
- Test issue querying by category functionality
- Validate path exclusion with glob patterns works correctly
- Confirm all existing methods produce expected output formats
- Ensure no MCP dependencies remain in the extracted code

## Agent Notes

**✅ COMPLETED SUCCESSFULLY**

**Implementation Summary:**
- Successfully extracted CoverityReportTool from original MCP server implementation
- Created clean module structure in `src/issue_parser/` with proper separation of concerns
- Removed all MCP dependencies (FastMCP, async tools) while preserving core functionality
- Fixed path pattern matching for directory exclusions to handle paths containing directory patterns
- Fixed error handling to properly raise ReportNotFoundError vs InvalidReportError

**Files Created:**
- `src/issue_parser/__init__.py` - Package initialization and exports
- `src/issue_parser/exceptions.py` - Custom exception classes
- `src/issue_parser/coverity_tool.py` - Core CoverityReportTool class (287 lines)

**Testing Verification:**
- All core functionality preserved and tested successfully
- JSON report loading with validation ✅
- Issue querying by category with case-insensitive matching ✅  
- Path exclusion with glob-style patterns ✅
- Issue formatting for pipeline consumption ✅
- Error handling with custom exceptions ✅
- Zero MCP dependencies confirmed ✅

**Ready for Integration:**
The extracted tool is ready for pipeline integration via the adapter layer (Task 2). All existing functionality from the proven MCP implementation has been preserved while removing server-specific dependencies. 