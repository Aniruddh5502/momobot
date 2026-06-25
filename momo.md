# Momobot Project Contract: momo.md

This document serves as the definitive technical reference for the Momobot agent to ensure portability, installability, and architectural coherence.

## 1. Libraries
The project depends on the following core libraries:
- **Core Logic & Orchestration:** `langgraph`, `langchain_core`, `langchain_ollama`, `pydantic`
- **LLM Backend:** `ollama` (Local LLM server)
- **Terminal UI & UX:** `rich`, `prompt_toolkit`
- **Web & Vision:** `playwright` (Headless Chromium), `bs4` (BeautifulSoup), `ddgs` (DuckDuckGo Search)
- **Document Processing:** `pdf2image`, `pillow` (Image handling)
- **Environment & Utils:** `python-dotenv`

## 2. File Index
### Root Directory
- `main.py`: Entry point; defines the LangGraph state machine and core agent loop.
- `setup.py`: Environment bootstrap; initializes directories, default prompts, and color palettes.
- `README.md`: General project overview and installation guide.
- `requirements.txt`: Python dependency list.

### `PROMPT/` (Prompt Engineering)
- `SOUL.md`: Core identity, "Prime Directive" of proactivity, and behavioral constraints.
- `SKILL.md`: Index of specialized operational rules (Code Writing, Graphing, Wiki, etc.).
- `SUB_SOUL.md`: Dedicated system prompt for autonomous sub-agents.

### `TOOLS/` (Capability Layer)
- `basic_tools.py`: Fundamental file operations and web retrieval.
- `str_replace_tool.py`: Surgical text replacement with diff outputs.
- `persistant_shell_tool.py`: Persistent `/bin/bash` (or pwsh) process for stateful shell execution.
- `view_image.py`: Interface for vision models and Playwright-based rendering.
- `ocr_tool.py`: PDF text extraction via vision-OCR models.
- `memory_tools.py`: Logic for the keyword-based memory shard system.
- `task_state_tool.py`: Implementation of the structured task planning and tracking system.
- `clarification_tool.py`: Interactive prompt system for resolving user ambiguity.
- `subagent_tool.py`: Logic for spawning independent agent instances.

### `VISUALS/` (Interface)
- `animation.py`: Visual feedback indicators (e.g., thinking spinners).
- `print.py`: Enhanced printing utilities for the terminal.

### `MEMORY/` & `WORKSPACE/`
- `MEMORY/`: Storage for long-term memory shards (`.md` files).
- `WORKSPACE/`: Directory for agent outputs, obsidian knowledge bases, and temporary files.

## 3. Architecture
Momobot is architected as a **StateGraph** using LangGraph. The system operates on a cyclic flow designed for autonomous tool use:

`START` $\to$ `USER_INPUT` $\to$ `REASONING` $\to$ `TOOL_NODE` $\to$ `REASONING` (loop)

**Key Architectural Components:**
- **Reasoning Node:** Interacts with the local Ollama LLM, injecting the system prompt, active task state, and conversation summary.
- **Tool Node:** A dispatcher that executes tool calls and returns results to the reasoning node.
- **Compaction Node:** A specialized state manager that triggers when `COMPACTION_THRESHOLD` is reached, summarizing old messages into a dense session summary to maintain context efficiency.
- **Local LLM Integration:** Uses `ChatOllama` to run models (e.g., `gemma4:31b-cloud`) locally, ensuring low latency and data privacy.

## 4. Design Choices
- **Proactivity over Passivity:** The "Prime Directive" shifts the agent from a "question-answering machine" to an "acting agent." It is designed to anticipate next steps and chain actions without constant user prompts.
- **Memory Sharding:** Instead of a single conversation log, Momobot uses a shard-based memory system. Information is stored in small, keyword-indexed Markdown files, allowing the agent to retrieve only relevant context.
- **Context Compaction:** To solve the "context window" problem, the agent implements an automatic summarization loop, converting old dialogue into a "Session State Summary" while keeping the most recent interactions verbatim.
- **Hierarchical Agency:** Complex tasks are delegated to sub-agents. Sub-agents operate with their own independent `task_state` and tools, preventing the main agent's reasoning chain from becoming fragmented.
- **Decoupled Prompting:** By separating "Soul" (Identity) from "Skills" (Capabilities), the agent's personality remains consistent while its technical abilities can be expanded via the `SKILL.md` index.

## 5. Code Structure
The codebase is organized into a strictly modular hierarchy:
- **Entry Layer (`main.py`):** High-level orchestration and state machine definition.
- **Boot Layer (`setup.py`):** Infrastructure setup and default asset creation.
- **Capability Layer (`TOOLS/`):** Each tool is a standalone module, making it easy to add, remove, or test individual functions without affecting the core loop.
- **Knowledge Layer (`PROMPT/`):** Markdown-based prompt files that act as the "cognitive configuration" of the agent.
- **Persistence Layer (`MEMORY/`, `WORKSPACE/`):** Decoupled storage for long-term memory and task artifacts.
