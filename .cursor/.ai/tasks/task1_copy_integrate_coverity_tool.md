---
id: 1
title: 'Copy and Integrate Existing CoverityReportTool'
status: inprogress
priority: critical
feature: Issue Parser
dependencies: []
assigned_agent: claude
created_at: "2025-06-10T05:39:44Z"
started_at: "2025-06-10T05:43:56Z"
completed_at: null
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