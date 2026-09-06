# Momobot 🤖

**Your Private, Local-First Autonomous Agent.**

Momobot is a high-performance, tool-augmented agentic AI assistant that runs entirely on your machine. Built with **LangGraph** and **Ollama**, it orchestrates complex, multi-step tasks using a persistent tool ecosystem and a custom long-term memory system—ensuring your data never leaves your hardware.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Ollama](https://img.shields.io/badge/Backend-Ollama-red.svg)](https://ollama.com/)

---

## 🌟 Why Momobot?

Most AI agents rely on cloud APIs, compromising privacy and incurring costs. Momobot flips the script by bringing the entire agentic loop local.

- **🔒 Total Privacy:** 100% local execution. No telemetry, no cloud leaks.
- **🛠 Tool-Augmented:** Direct access to your filesystem, a persistent shell, web search, and vision/OCR capabilities.
- **🧠 Persistent Memory:** Uses "memory shards" to remember preferences and project contexts across sessions.
- **📋 Structured Planning:** A built-in Task State manager that allows the agent to plan, track, and recover from failures autonomously.
- **📉 Context Optimization:** Intelligent token compaction keeps the conversation healthy without losing critical session history.

---

## 🚀 Quick Start

Get Momobot running in three simple steps:

### 1. Clone & Install
```bash
git clone https://github.com/Aniruddh5502/momobot.git
cd momobot
pip install -e .
```

### 2. Environment Setup
Install the browser engine for vision and web tools:
```bash
playwright install chromium
```

### 3. Initialize & Run
Run the initialization wizard to configure your model and workspace:
```bash
momobot-init
```
Then, start your agent:
```bash
momobot
```

---

## 💻 Model Recommendations

Momobot works best with high-reasoning models. Choose a model based on your available system RAM:

| Profile | Recommended Model | Min. RAM | Experience |
|---|---|---|---|
| **Ultra** | `gemma4:31b-cloud` | 24GB+ | Complex reasoning, high accuracy |
| **Balanced** | `llama3:8b` | 8GB - 16GB | Fast, reliable for most tasks |
| **Light** | `phi3` or `mistral` | 4GB - 8GB | Basic automation, very fast |

*Note: Pull your chosen model first via `ollama pull <model_name>`.*

---

## 🛠 What can Momobot do?

Stop thinking in "prompts" and start thinking in **workflows**. 

- **Local Codebase Auditor:** *"Scan my `/src` folder, find all TODOs in the comments, and summarize them into a `backlog.md` file."*
- **Research Assistant:** *"Search the web for the latest trends in MEMS accelerometers, extract the key specifications, and save them to my long-term memory."*
- **Document Processor:** *"OCR this PDF manual, find the troubleshooting section, and write a simplified guide in Markdown."*
- **System Automator:** *"Check the current system logs for errors, identify the root cause, and suggest a fix using the persistent shell."*

---

## ⚙️ Technical Architecture

Momobot utilizes a cyclic graph structure via **LangGraph** to ensure robust task execution:

`START` $\rightarrow$ `USER_INPUT` $\rightarrow$ `REASONING` $\rightarrow$ `TOOL_NODE` $\rightarrow$ `COMPACT` $\rightarrow$ `END`

### The Tech Stack
- **Orchestration:** `langgraph`, `langchain-ollama`
- **Interface:** `rich`, `prompt_toolkit`
- **Capabilities:** `playwright` (Web/Vision), `ddgs` (Search), `pdf2image` (OCR)
- **State Management:** Local JSON for task tracking, Markdown for semantic memory.

### Tool Index
| Category | Tools | Purpose |
|---|---|---|
| **Filesystem** | `read_file`, `write_file`, `str_replace_tool`, `list_directory` | Surgical file editing and management |
| **System** | `bash_shell` | Persistent process for CLI operations |
| **Memory** | `save_memory`, `recall_memory`, `modify_memory` | Long-term knowledge retrieval |
| **Intelligence** | `subagent`, `ask_clarifying_questions` | Task decomposition and ambiguity resolution |
| **External** | `web_search`, `web_fetch`, `view_image`, `ocr_pdf` | Interacting with the real world |

---

## 🛠 Configuration & Usage

### Internal Commands
While chatting, you can use special flags to modify agent behavior:
- `/think` — Forces the agent into deep reasoning mode for complex logic.

### Settings
Top-level constants (Model, Context Window, Compaction Threshold) can be adjusted in `main.py` or during the `momobot-init` process.

---

## 🗺 Roadmap
- [ ] **LiteLLM Integration:** Support for hybrid local/cloud backends.
- [ ] **Web UI:** A Streamlit-based dashboard to visualize Task State and Memory.
- [ ] **Auto-Configuration:** Automatic hardware detection for model suggestions.
- [ ] **Plugin System:** Allow users to drop new Python tools into the `TOOLS/` folder for auto-loading.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.
