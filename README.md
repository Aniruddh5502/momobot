# Momobot

> This one we are going to use for agent eval and harness eval

Momobot is a cynical AI Agent designed with a deterministic verification harness. Unlike typical AI agents, Momobot distrusts assumptions and requires evidence from the environment, tool responses, or shell command results before committing to a conclusion.

## Stability and Reliability

Momobot implements a rigorous stability framework called the Deterministic Verification Harness. Unlike typical agents that mark a task as "done" based on their own internal confidence, Momobot requires external proof:

- Verification Commands: Every task is initialized with a `verify_cmd` (a shell command).
- Hard Evidence: A task is only marked as `done` if the `verify_cmd` returns a zero exit code.
- Failure Recovery: If verification fails, the agent cannot simply ignore it; it must use the `task_replan` tool to analyze the failure and propose a new set of corrective tasks.
- Cycle & Dependency Detection: The harness prevents logic loops by detecting dependency cycles and ensuring tasks are executed in the correct order.

## Installation

### Prerequisites
- Python 3.10 or higher
- Ollama (if using the default configuration)

### Editable Installation
To install Momobot in editable mode (recommended for development), run the following command from the project root:

```bash
pip install -e .
```

Alternatively, you can install the dependencies from the requirements file:

```bash
pip install -r requirements.txt
```

## Configuration

Configuration is managed via `config.py` and stored in `config/config.json`. You can modify the following settings:

- `provider`: The LLM provider (e.g., `ollama`).
- `model`: The specific model to use (e.g., `gemma4:31b-cloud`).
- `base_url`: The API endpoint for the LLM.
- `recent_window`: The context window size for conversation history.
- Prompt paths: Paths to `soul.md`, `compaction.md`, and `user.md`.

## Usage

Once installed, you can invoke the bot using the registered script:

```bash
momobot
```

## Project Structure

- `core/`: Main agent logic and orchestration.
- `tools/`: Environment interaction tools.
- `ui/`: Command line interface and user interaction.
- `cmd/`: Internal command handling.
- `utils/`: Helper functions and shared utilities.
- `prompts/`: System identity and behavioral guidelines (the "soul" of the bot).
- `sessions/`: Local database for session persistence.
- `states/`: Runtime state tracking.
