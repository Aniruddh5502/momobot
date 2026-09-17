# Command System Implementation Plan

This document outlines the architecture and expansion strategy for the Momobot Command Registry system.

## 1. Architecture Overview
The system follows a **Registry Pattern**, decoupling the user input handling from the command logic. This ensures that adding new functionality does not require modifying the core graph orchestration in `main.py`.

### Data Flow
`User Input` $\rightarrow$ `main.py (inputNode)` $\rightarrow$ `CommandRegistry` $\rightarrow$ `Command Handler` $\rightarrow$ `State Update` $\rightarrow$ `LangGraph Router`

## 2. Core Components

### `CMD/registry.py` (The Orchestrator)
- **Responsibility**: Maps slash commands (e.g., `/session`) to Python functions.
- **Key Logic**: 
    - Handles exact matches.
    - Handles pattern matches (e.g., `/session1` matches `/session` with arg `1`).
    - Returns a state update dictionary if a command is executed, otherwise `None`.

### `CMD/session_cmds.py` (The Implementation)
- **Responsibility**: Contains specific logic for session management.
- **Key Commands**:
    - `/session` or `/sessions`: Lists available sessions or resumes a specific one by index.

### `main.py` (The Integration)
- **Responsibility**: Initializes the registry and passes the current `state` and `context` (including `SessionManager`) to the registry during the `inputNode` phase.

## 3. Command Control Signals (Atomic API)
Command handlers must return a dictionary that informs the graph's next transition:

| Return Value | Graph Route | Purpose |
| :--- | :--- | :--- |
| `{"skip": True}` | `input` $\rightarrow$ `input` | UI-only commands; prevents AI from responding. |
| `{"skip": False}` | `input` $\rightarrow$ `reasoning` | State changes that should trigger AI processing. |
| `{"end": "end_loop"}` | `input` $\rightarrow$ `END` | Graceful termination of the agent loop. |
| `{"messages": [...]}` | $\text{Update State}$ | Modifies or clears the conversation history. |

## 4. Expansion Guide (Adding New Commands)
To add new commands without altering the core engine:
1. **Create a Handler**: Define a function with signature `(args, state, context)`.
2. **Register**: Use the `@registry.register("/command_name")` decorator.
3. **Define Outcome**: Return the appropriate control signal (`skip`, `end`, or state updates).
4. **Plug-in**: Call the registration function in `main.py` during initialization.

## 5. Proposed Command Roadmap
Here are suggested commands to integrate, categorized by their utility:

### State & History Management
- `/clear`: Wipes current session messages. `{"messages": [], "skip": True}`
- `/reset`: Resets the entire agent state (summary, token counts) to initial.
- `/undo`: Removes the last AI response and the last user prompt.

### System & Diagnostics
- `/tokens`: Displays current `token_usages` and `summary` length.
- `/system`: Prints current `systemInfo` (OS, Python version, etc.).
- `/status`: Shows if the agent is in `reasoning` mode or `standard` mode.

### Session Utilities
- `/save [name]`: Manually names and saves the current session.
- `/delete [index/name]`: Permanently removes a saved session file.
- `/export`: Dumps the current session state to a shareable JSON/Markdown file.

### Agent Control
- `/think`: (Already exists in inputNode, but could be formalized as a command for specific prompt injection).
- `/force`: Forces the agent to ignore the summary and re-read the full message history.

## 6. Verification State
- [x] Command Registry Base implemented.
- [x] Session Commands implemented.
- [x] `main.py` integration completed.
- [x] Session resume loop bug fixed.
