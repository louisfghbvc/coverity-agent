# Task 5: Assemble Agent

**Objective**: Integrate all components (tools, model, instructions) to build the final, executable agent.

**Parent Plan**: [PLAN.md](../plans/PLAN.md)

**Status**: To Do

**Assignee**:

**Dependencies**:
-   Task 2: Implement Tools
-   Task 3: Configure NIM Model
-   Task 4: Develop Agent Instructions

---

### Description

This is the integration step. A main script (e.g., `main.py`) will be created to:
1.  Import the custom tools from their module.
2.  Import the initialized NIM model object.
3.  Import the agent's instructions prompt.
4.  Call `deepagents.create_deep_agent`, passing all the imported components as arguments.
5.  Add the invocation logic (e.g., `agent.invoke(...)`) to kick off the agent's task with an initial user message.

### Acceptance Criteria

-   A `main.py` script exists that successfully assembles and creates the agent.
-   The script can be executed from the command line.
-   When run, the agent starts its operational loop as defined in the instructions.
-   The agent correctly uses the tools and the NIM model to attempt to fix at least one error.
