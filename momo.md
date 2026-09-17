# Project: Momobot
Local autonomous agent built with LangGraph and Ollama.

## Code Style
- Modular tools in `TOOLS/`
- State-based orchestration via LangGraph
- Markdown-based prompt governance in `PROMPT/`
- Use `rich` for console output and `prompt_toolkit` for multi-line input.

## Commands
- Run: `python main.py`
- Setup: `python bootstrap.py`

## Architecture
- `main.py`: Core LangGraph state machine and entry point.
- `bootstrap.py`: Environment initialization, directory setup, and prompt generation.
- `PROMPT/`: System identity (`SOUL.md`), skill index (`SKILL.md`), and compaction prompts.
- `TOOLS/`: Atomic capabilities (shell, file ops, memory, subagents).
- `VISUALS/`: Console UI elements (animations, smart printing).
- `MEMORY/`: Persistent flat-file semantic storage.
- `STATE/`: Task state and session persistence.
- `WORKSPACE/`: Working directory for outputs and skills.
- `CONVERSATION/`: Dialogue history logs.

## Important Notes
- Proactivity is the prime directive: act, then report.
- Memory is keyword-indexed Markdown shards.
- Context is managed via a compaction node when token thresholds are met.
- Subagents are spawned for isolated, complex tasks without persistent conversation memory.
