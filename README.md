# Momobot

A local-first agentic AI assistant built on LangGraph and Ollama. Momobot runs entirely on your machine, orchestrates multi-step tasks with a persistent tool ecosystem, and manages its own memory across sessions — no cloud required.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   LangGraph Graph                   │
│                                                     │
│  START → USER_INPUT → REASONING → TOOL_NODE ──┐     │
│              ↑            │                   │     │
│              │          (no tools)            │     │
│              │            ↓                   │     │
│            COMPACT ←────────────────────────────    │
│              ↓                                      │
│             END                                     │
└─────────────────────────────────────────────────────┘
```

The graph has four nodes:

- **USER_INPUT** — Reads multiline input via `prompt_toolkit` (Enter for newline, Esc+Enter to submit). Handles exit commands gracefully.
- **REASONING** — Calls the LLM with the full system prompt, live task state, optional conversation summary, and message history. Retries up to 5× on Ollama 5xx errors.
- **TOOL_NODE** — LangGraph's `ToolNode` dispatches all tool calls from the LLM's response.
- **COMPACT** — When token usage exceeds the compaction threshold, older messages are summarized into a rolling `summary` field and removed from the message list, keeping the context window healthy.

---

## Tech Stack

| Component | Library |
|---|---|
| Agent graph | `langgraph` |
| LLM backend | `langchain-ollama` + Ollama (local) |
| Terminal UI | `rich`, `prompt_toolkit` |
| Shell tool | `/bin/bash`, persistent process |
| Vision / OCR | `ollama` (vision model), `pdf2image` |
| Browser rendering | `playwright` (headless Chromium) |
| PDF parsing | LlamaCloud API |
| Web search | `ddgs` (DuckDuckGo) |

Default model: `gemma4:31b-cloud` — swap via the `MODEL` constant in `main.py`.

---

## Tool Reference

### File Tools
| Tool | Description |
|---|---|
| `read_file` | Read any file in the workspace |
| `write_file` | Write/overwrite a file; creates parent directories |
| `str_replace_tool` | Surgical in-place edits — finds a unique string and replaces it; returns a unified diff |
| `list_directory` | List files and folders at any workspace path |

### Shell
| Tool | Description |
|---|---|
| `bash_shell` | Persistent `/bin/bash` process; state (cwd, env vars, venvs) survives across calls. **Read/execute only** — file writes are blocked and delegated to `write_file`. |

### Memory
The memory system stores and retrieves named "shards" — markdown files indexed by keyword and timestamp.

| Tool | Description |
|---|---|
| `save_memory` | Write a new memory shard with a keyword and note |
| `recall_memory` | Return the full memory store |
| `modify_memory` | Overwrite the content of an existing shard |
| `delete_memory` | Remove a shard and its entry from the map |

Memory lives in `MEMORY_DIR/MEMORY.md`.

### Task State
Gives the agent a structured plan it can track, update, and recover from across the entire session. State is persisted to `task_state.json` with audit logging to `task_state_audit.jsonl`.

| Tool | Description |
|---|---|
| `init_task` | Create a new plan with a goal and ordered steps (supports `depends_on` for blocking) |
| `read_task_state` | Read the current plan as JSON |
| `complete_step` | Mark a step done with an optional result string |
| `fail_step` | Mark a step failed with a reason; triggers automatic status propagation |
| `replan_task` | Remove failed/obsolete steps and add new ones — adapts without starting over |
| `erase_task_state` | Clear the state file entirely |

Step statuses: `pending → running → done / failed / blocked`. Blocked steps automatically unblock when all their dependencies complete.

### Vision & OCR
| Tool | Description |
|---|---|
| `view_image` | Analyze any image or browser-rendered file (PNG, JPEG, SVG, HTML) using a vision model. Playwright renders SVG/HTML to a screenshot first. Accepts a `prompt` to direct what the model looks for. |
| `ocr_pdf` | Extract text from a PDF using a vision OCR model page-by-page. Saves each page as a numbered `.md` file in `<stem>_ocr/`. |

### Web
| Tool | Description |
|---|---|
| `web_search` | DuckDuckGo search; returns titles, snippets, and URLs |
| `web_fetch` | Fetch a full webpage via headless Chromium (handles JS-rendered pages); strips boilerplate and returns clean text |

### Subagent
| Tool | Description |
|---|---|
| `subagent` | Spawn a fully independent agent with its own LangGraph loop and access to all base tools. Use for parallelisable or self-contained subtasks. |

### Clarification
| Tool | Description |
|---|---|
| `ask_clarifying_questions` | Pause execution and ask the user a list of questions interactively. Returns answers as a keyed dict. Handles vague responses with a follow-up prompt. |

### PDF Parsing
| Tool | Description |
|---|---|
| `parse_pdf` | High-quality structured PDF extraction via LlamaCloud (requires `Parser_API` env var). Returns full markdown. |

---

## Context Management

Momobot tracks token usage from Ollama's `prompt_eval_count` metadata. When it crosses `COMPACTION_THRESHOLD` (default 100,000 tokens):

1. All messages except the most recent `RECENT_WINDOW` (default 6) are passed to a bare LLM instance.
2. The LLM produces a dense "Session State Summary" — preserving decisions, constraints, and goals.
3. Compressed messages are removed from the state; the summary is prepended to future system prompts.
4. A new summary extends the running one rather than replacing it.

---

## Configuration

All top-level constants live in `main.py`:

```python
MODEL                = "gemma4:31b-cloud"   # Ollama model tag
BASE_URL             = "http://localhost:11434"
CTX_WINDOW           = 262144               # Ollama num_ctx
STREAM               = True
COMPACTION_THRESHOLD = 100000              # tokens before compaction
RECENT_WINDOW        = 6                    # messages to keep post-compaction
```

Workspace and memory paths are configured in `setup.py`. Secrets (`Parser_API` for LlamaCloud) are loaded from a `.env` file via `python-dotenv`.

---

## Project Structure

```
momobot/
├── main.py                     # Entry point, LangGraph graph definition
├── setup.py                    # Paths, system prompts, color palette
├── TOOLS/
│   ├── basic_tools.py          # read_file, write_file, web_search, web_fetch,
│   │                           #   list_directory, parse_pdf
│   ├── str_replace_tool.py     # In-place file editing with diff output
│   ├── persistant_shell_tool.py# Persistent Bash tool
│   ├── view_image.py           # Vision analysis + Playwright rendering
│   ├── ocr_tool.py             # PDF OCR via vision model
│   ├── memory_tools.py         # Long-term memory shard system
│   ├── task_state_tool.py      # Structured task planning and tracking
│   ├── clarification_tool.py   # Interactive user question prompts
│   └── subagent_tool.py        # Nested agent spawning
├── VISUALS/
│   ├── animation.py            # Thinking spinner
│   └── print.py                # Smart print helpers
└── MEMORY/
    └── MEMORY.md               # Memory store
```

---

## Installation & Running

### Current Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install browser for vision/web tools
playwright install chromium

# Start Ollama and pull your model
ollama pull gemma4:31b-cloud

# Run
python main.py
```

### 🚀 Roadmap: Simplified Installation
I am currently working toward making Momobot as installable as a standard package. The goal is to move away from manual file edits in `setup.py` and long pip strings.

**Future target:**
```bash
pip install momobot-agent
momobot init  # Sets up workspace and pulls models
momobot run   # Starts the agent
```
This will involve packaging the project as a Python module, implementing a CLI for configuration, and automating the Ollama model pull process.

---

## Notes
# Momobot

A local-first agentic AI assistant built on LangGraph and Ollama. Momobot runs entirely on your machine, orchestrates multi-step tasks with a persistent tool ecosystem, and manages its own memory across sessions — no cloud required.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   LangGraph Graph                   │
│                                                     │
│  START → USER_INPUT → REASONING → TOOL_NODE ──┐     │
│              ↑            │                   │     │
│              │          (no tools)            │     │
│              │            ↓                   │     │
│            COMPACT ←────────────────────────────    │
│              ↓                                      │
│             END                                     │
└─────────────────────────────────────────────────────┘
```

The graph has four nodes:

- **USER_INPUT** — Reads multiline input via `prompt_toolkit` (Enter for newline, Esc+Enter to submit). Handles exit commands gracefully.
- **REASONING** — Calls the LLM with the full system prompt, live task state, optional conversation summary, and message history. Retries up to 5× on Ollama 5xx errors.
- **TOOL_NODE** — LangGraph's `ToolNode` dispatches all tool calls from the LLM's response.
- **COMPACT** — When token usage exceeds the compaction threshold, older messages are summarized into a rolling `summary` field and removed from the message list, keeping the context window healthy.

---

## Tech Stack

| Component | Library |
|---|---|
| Agent graph | `langgraph` |
| LLM backend | `langchain-ollama` + Ollama (local) |
| Terminal UI | `rich`, `prompt_toolkit` |
| Shell tool | PowerShell 7 (`pwsh.exe`), persistent process |
| Vision / OCR | `ollama` (vision model), `pdf2image` |
| Browser rendering | `playwright` (headless Chromium) |
| PDF parsing | LlamaCloud API |
| Web search | `ddgs` (DuckDuckGo) |

Default model: `gemma4:31b-cloud` — swap via the `MODEL` constant in `main.py`.

---

## Tool Reference

### File Tools
| Tool | Description |
|---|---|
| `read_file` | Read any file in the workspace |
| `write_file` | Write/overwrite a file; creates parent directories |
| `str_replace_tool` | Surgical in-place edits — finds a unique string and replaces it; returns a unified diff |
| `list_directory` | List files and folders at any workspace path |

### Shell
| Tool | Description |
|---|---|
| `bash_shell` | Persistent `pwsh.exe` process; state (cwd, env vars, venvs) survives across calls. **Read/execute only** — file writes are blocked and delegated to `write_file`. Pass `__reset_shell__` to recover from failures. |

### Memory
The memory system stores and retrieves named "shards" — markdown files indexed by keyword and timestamp.

| Tool | Description |
|---|---|
| `save_memory` | Write a new memory shard with a keyword and note |
| `recall_memory` | Return the full memory map (all keywords + filenames) |
| `read_memory` | Read a specific shard by filename |
| `modify_memory` | Overwrite the content of an existing shard |
| `delete_memory` | Remove a shard and its entry from the map |

Memory files live in `MEMORY_DIR/memory_files/` and the index at `MEMORY_DIR/MEMORY.md`.

### Task State
Gives the agent a structured plan it can track, update, and recover from across the entire session. State is persisted to `task_state.json` with audit logging to `task_state_audit.jsonl`.

| Tool | Description |
|---|---|
| `init_task` | Create a new plan with a goal and ordered steps (supports `depends_on` for blocking) |
| `read_task_state` | Read the current plan as JSON |
| `complete_step` | Mark a step done with an optional result string |
| `fail_step` | Mark a step failed with a reason; triggers automatic status propagation |
| `replan_task` | Remove failed/obsolete steps and add new ones — adapts without starting over |
| `erase_task_state` | Clear the state file entirely |

Step statuses: `pending → running → done / failed / blocked`. Blocked steps automatically unblock when all their dependencies complete.

### Vision & OCR
| Tool | Description |
|---|---|
| `view_image` | Analyze any image or browser-rendered file (PNG, JPEG, SVG, HTML) using a vision model. Playwright renders SVG/HTML to a screenshot first. Accepts a `prompt` to direct what the model looks for. |
| `ocr_pdf` | Extract text from a PDF using a vision OCR model page-by-page. Saves each page as a numbered `.md` file in `<stem>_ocr/`. |

### Web
| Tool | Description |
|---|---|
| `web_search` | DuckDuckGo search; returns titles, snippets, and URLs |
| `web_fetch` | Fetch a full webpage via headless Chromium (handles JS-rendered pages); strips boilerplate and returns clean text |

### Subagent
| Tool | Description |
|---|---|
| `subagent` | Spawn a fully independent agent with its own LangGraph loop and access to all base tools. Use for parallelisable or self-contained subtasks. |

### Clarification
| Tool | Description |
|---|---|
| `ask_clarifying_questions` | Pause execution and ask the user a list of questions interactively. Returns answers as a keyed dict. Handles vague responses with a follow-up prompt. |

### PDF Parsing
| Tool | Description |
|---|---|
| `parse_pdf` | High-quality structured PDF extraction via LlamaCloud (requires `Parser_API` env var). Returns full markdown. |

---

## Context Management

Momobot tracks token usage from Ollama's `prompt_eval_count` metadata. When it crosses `COMPACTION_THRESHOLD` (default 50,000 tokens):

1. All messages except the most recent `RECENT_WINDOW` (default 6) are passed to a bare LLM instance.
2. The LLM produces a dense "Session State Summary" — preserving decisions, constraints, and goals.
3. Compressed messages are removed from the state; the summary is prepended to future system prompts.
4. A new summary extends the running one rather than replacing it.

This keeps the context window from growing unbounded while preserving essential session context.

---

## Configuration

All top-level constants live in `main.py`:

```python
MODEL                = "gemma4:31b-cloud"   # Ollama model tag
BASE_URL             = "http://localhost:11434"
CTX_WINDOW           = 262144               # Ollama num_ctx
STREAM               = True
COMPACTION_THRESHOLD = 50000                # tokens before compaction
RECENT_WINDOW        = 6                    # messages to keep post-compaction
```

Workspace and memory paths are configured in `setup.py` via `WORKSPACE_DIR` and `MEMORY_DIR`.

Secrets (`Parser_API` for LlamaCloud) are loaded from a `.env` file via `python-dotenv`.

---

## Project Structure

```
momobot/
├── main.py                     # Entry point, LangGraph graph definition
├── setup.py                    # Paths, system prompts, color palette
├── TOOLS/
│   ├── basic_tools.py          # read_file, write_file, web_search, web_fetch,
│   │                           #   list_directory, parse_pdf, task_complete
│   ├── str_replace_tool.py     # In-place file editing with diff output
│   ├── persistant_shell_tool.py# Persistent PowerShell tool
│   ├── view_image.py           # Vision analysis + Playwright rendering
│   ├── ocr_tool.py             # PDF OCR via vision model
│   ├── memory_tools.py         # Long-term memory shard system
│   ├── task_state_tool.py      # Structured task planning and tracking
│   ├── clarification_tool.py   # Interactive user question prompts
│   └── subagent_tool.py        # Nested agent spawning
├── VISUALS/
│   ├── animation.py            # Thinking spinner
│   └── print.py                # Smart print helpers
└── MEMORY/
    ├── MEMORY.md               # Memory index (keyword | timestamp | filename)
    └── memory_files/           # Individual memory shards (.md)
```

---

## Running

```bash
# Install dependencies
pip install langchain-ollama langgraph langchain-core rich prompt_toolkit \
            playwright ddgs beautifulsoup4 pdf2image pillow ollama python-dotenv \
            pydantic termcolor

playwright install chromium

# Configure paths and prompts
# Edit setup.py — set WORKSPACE_DIR, MEMORY_DIR, system_prompt, sub_agent_sys_prompt

# Start Ollama and pull your model
ollama pull gemma4:31b-cloud

# Run
python main.py
```

To exit the session, type `x`, `exit`, `quit`, or `end` at the prompt, or leave the input empty.

---

## Notes

- The persistent shell (`bash_shell`) uses `pwsh.exe` and is designed for Windows. On Linux/macOS, replace the `_start_shell()` function target with `bash` or `zsh`.
- The shell blocks all file-write operations by regex — writes go through `write_file` or `str_replace_tool` for traceability.
- `str_replace_tool` requires that `old_str` appears **exactly once** in the target file. For repeated strings, add surrounding context to make it unique.
- OCR uses `glm-ocr:q8_0` — pull it via Ollama separately from the main reasoning model.
- Vision analysis in `view_image` uses the same model as reasoning (`VISION_MODEL = "gemma4:31b-cloud"`).
- The persistent shell (`bash_shell`) is anchored to the workspace.
- The shell blocks all file-write operations by regex — writes go through `write_file` or `str_replace_tool` for traceability.
- `str_replace_tool` requires that `old_str` appears **exactly once** in the target file.
- OCR uses `glm-ocr:q8_0` — pull it via Ollama separately from the main reasoning model.
- Vision analysis in `view_image` uses the same model as reasoning.
