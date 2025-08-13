# Task 4: Develop Agent Instructions

**Objective**: Write a clear, detailed, and robust set of instructions (the system prompt) to guide the agent's behavior.

**Parent Plan**: [PLAN.md](../plans/PLAN.md)

**Status**: To Do

**Assignee**:

**Dependencies**:
-   Task 2: Implement Tools

---

### Description

The quality of the agent's instructions is paramount to its success. This task involves writing the main prompt that will be passed to the `create_deep_agent` function. The prompt must:
-   Define the agent's role and primary goal (e.g., "You are an expert security developer...").
-   Clearly list the available tools and how to use them.
-   Specify the exact, step-by-step workflow loop (scan -> analyze -> read -> fix -> write -> loop).
-   Provide rules for handling edge cases, such as what to do if a fix fails or if no errors are found.

### Acceptance Criteria

-   A final, well-documented prompt is stored as a string variable in a configuration file (e.g., `prompts.py`).
-   The prompt explicitly mentions all custom tools and their expected inputs/outputs.
-   The workflow described in the prompt is unambiguous and aligns with the project plan.
-   The prompt is reviewed and refined to be as clear and effective as possible.
