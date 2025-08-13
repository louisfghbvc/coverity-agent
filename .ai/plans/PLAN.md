# Coverity Auto-Fix Agent: Project Plan

## 1. Project Vision

To develop an autonomous AI agent, powered by `deepagents` and NVIDIA NIM models, capable of automatically detecting, analyzing, and fixing security vulnerabilities reported by the Coverity static analysis tool. The agent will operate in a continuous loop of analysis, repair, and verification, significantly accelerating the remediation of security debt.

## 2. Core Features (MVP)

The initial version of the agent will focus on a core, end-to-end workflow.

-   **F1: Coverity Integration**: The agent can execute Coverity scans and parse the resulting error reports.
-   **F2: Code Interaction**: The agent can read and write files from the local filesystem to analyze and patch code.
-   **F3: LLM-Powered Repair**: The agent leverages a large language model (NIM `gpt-oss-20b`) to generate code fixes based on Coverity reports.
-   **F4: Automated Workflow**: The agent autonomously orchestrates the scan -> analyze -> fix -> verify loop.
-   **F5: Model Swapping**: The architecture supports easily changing the underlying language model.

## 3. Agent Architecture

The system will be built around the `deepagents` framework, which provides planning, sub-agents, and a file system interface.

```mermaid
graph TD
    subgraph Agent Core
        A[Main Agent]
        T[Tools]
        M[Model: NIM gpt-oss-20b]
        P[Prompt/Instructions]
    end

    subgraph Custom Tools
        T1[run_coverity_scan()]
        T2[read_actual_file()]
        T3[write_actual_file()]
    end

    A -- uses --> T
    A -- powered by --> M
    A -- guided by --> P
    T -- contains --> T1
    T -- contains --> T2
    T -- contains --> T3

    subgraph Workflow Loop
        direction LR
        S1[1. Run Scan] --> S2[2. Get Errors]
        S2 --> S3[3. Pick First Error]
        S3 --> S4[4. Read File]
        S4 --> S5[5. Generate Fix]
        S5 --> S6[6. Write File]
        S6 --> S1
    end

    A -- executes --> S1

```

## 4. Technical Stack

-   **Core Framework**: `deepagents`
-   **Language Model**: NVIDIA NIM (`gpt-oss-20b` or similar, e.g., `ai-mistral-large`) via `langchain-nvidia-ai-endpoints`
-   **Static Analysis**: Coverity
-   **Language**: Python 3.x
-   **Dependencies**: `langchain`, `langchain_core`

## 5. High-Level Task Breakdown

1.  **Setup & Configuration (`task1_setup_environment.md`)**:
    -   Install all Python dependencies.
    -   Set up environment variables for NVIDIA NIM (`NVIDIA_API_KEY`, `NIM_ENDPOINT_URL`).

2.  **Tool Development (`task2_implement_tools.md`)**:
    -   Implement `run_coverity_scan` tool, including a parser for Coverity's output.
    -   Implement `read_actual_file` and `write_actual_file` tools for real filesystem interaction.

3.  **Model Integration (`task3_configure_nim_model.md`)**:
    -   Write the code to initialize the `NVIDIA_NIM` LangChain object.
    -   Ensure it can be correctly passed to the `create_deep_agent` function.

4.  **Agent Prompting (`task4_develop_agent_instructions.md`)**:
    -   Craft the detailed system prompt (`instructions`) that defines the agent's workflow, personality, and goals.

5.  **Main Agent Assembly (`task5_assemble_agent.md`)**:
    -   Write the main script that imports all components (tools, model, instructions) and calls `create_deep_agent`.
    -   Add the invocation logic to start the agent's loop.

6.  **Testing & Evaluation (`task6_test_and_evaluate.md`)**:
    -   Prepare a sample codebase with known Coverity errors.
    -   Run the agent and evaluate its ability to fix the errors.
    -   Iterate on prompts and tools based on performance.
