import re
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, Tuple

@dataclass
class CommandResult:
    """What a slash-command returns to the CLI.

    handled: True  → the CLI should NOT forward to the agent.
    state:   If set, replaces the current AgentState.
    render:  If True, the CLI should re-render the full message history
             (used when resuming a session).
    """
    handled: bool = True
    state: Optional[Dict[str, Any]] = None
    render: bool = False


# Type alias for a command handler: (args: str, state: dict, context: dict) -> state_update
CommandHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Any]

class CommandRegistry:
    def __init__(self):
        self._commands: Dict[str, Tuple[CommandHandler, str]] = {}

    def register(self, name: str, description: str = "No description provided."):
        def wrapper(func: CommandHandler):
            cmd_name = name if name.startswith("/") else f"/{name}"
            self._commands[cmd_name] = (func, description)
            return func
        return wrapper

    def execute(self, text: str, state: Dict[str, Any], context: Dict[str, Any]) -> Optional[CommandResult]:
        if not text.startswith("/"):
            return None

        parts = text.split(" ", 1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd_name in self._commands:
            handler, _ = self._commands[cmd_name]
            return self._normalize(handler(args, state, context))

        # Prefix match (e.g. /session1 -> /session with args "1")
        for registered_cmd in self._commands:
            if cmd_name.startswith(registered_cmd) and registered_cmd.startswith("/"):
                suffix_args = cmd_name[len(registered_cmd):] + (" " + args if args else "")
                handler, _ = self._commands[registered_cmd]
                return self._normalize(handler(suffix_args, state, context))

        return None

    @staticmethod
    def _normalize(result) -> Optional[CommandResult]:
        if result is None:
            return CommandResult()
        if isinstance(result, CommandResult):
            return result
        # Backwards-compat: a bare dict is treated as a state replacement.
        if isinstance(result, dict):
            return CommandResult(state=result)
        return CommandResult()

    def list_commands(self) -> Dict[str, str]:
        return {name: desc for name, (func, desc) in self._commands.items()}