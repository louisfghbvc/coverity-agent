# Task 2: Implement Tools

**Objective**: Develop and test the custom tools that the agent will use to interact with the local environment (Coverity and the filesystem).

**Parent Plan**: [PLAN.md](../plans/PLAN.md)

**Status**: To Do

**Assignee**:

**Dependencies**:
-   Task 1: Setup & Configuration

---

### Description

This is a critical task that involves creating three core tools:
1.  **`run_coverity_scan(directory: str)`**: This tool will execute the Coverity command-line interface, capture the output, and parse it into a structured, human-readable format that the LLM can easily understand. The parser needs to be robust.
2.  **`read_actual_file(filepath: str)`**: A tool to read the contents of a specified file from the real filesystem.
3.  **`write_actual_file(filepath: str, content: str)`**: A tool to write content back to a file on the real filesystem. For safety, this might initially include a human-in-the-loop confirmation step.

### Acceptance Criteria

-   All three tools (`run_coverity_scan`, `read_actual_file`, `write_actual_file`) are implemented as Python functions with the `@tool` decorator.
-   `run_coverity_scan` can correctly execute a scan on a sample project and parse the JSON/XML output into a clean string format.
-   `read_actual_file` and `write_actual_file` can successfully read from and write to the local disk.
-   Unit tests are created for each tool to ensure they function as expected.
