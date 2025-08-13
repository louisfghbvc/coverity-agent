# Task 3: Configure NIM Model

**Objective**: Integrate the specified NVIDIA NIM model into the agent's framework.

**Parent Plan**: [PLAN.md](../plans/PLAN.md)

**Status**: To Do

**Assignee**:

**Dependencies**:
-   Task 1: Setup & Configuration

---

### Description

This task focuses on initializing the language model that will power the agent. It involves:
1.  Importing `NVIDIA_NIM` from `langchain_nvidia_ai_endpoints`.
2.  Writing the code to instantiate the model object, specifying the model ID (e.g., `ai-mistral-large` or the specific ID for `gpt-oss-20b`).
3.  Ensuring that this model object can be seamlessly passed to the `create_deep_agent` function during the agent's assembly.

### Acceptance Criteria

-   A Python module exists (e.g., `llm_config.py`) that contains the model initialization logic.
-   The code correctly loads the `NVIDIA_API_KEY` and `NIM_ENDPOINT_URL` from the environment.
-   The instantiated `NVIDIA_NIM` object is successfully created without errors.
-   The model object is confirmed to be compatible with the `model` parameter of the `deepagents.create_deep_agent` function.
