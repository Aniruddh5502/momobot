import re
from typing import Callable, Dict, Any, Optional, Tuple

# Type alias for a command handler: (args: str, state: dict, context: dict) -> state_update
CommandHandler = Callable[[str, Dict[str, Any], Dict[str, Any]], Any]

class CommandRegistry:
    def __init__(self):
        self._commands: Dict[str, CommandHandler] = {}

    def register(self, name: str):
        """Decorator to register a function as a slash command."""
        def wrapper(func: CommandHandler):
            # Ensure command starts with /
            cmd_name = name if name.startswith("/") else f"/{name}"
            self._commands[cmd_name] = func
            return func
        return wrapper

    def execute(self, text: str, state: Dict[str, Any], context: Dict[str, Any]) -> Optional[Any]:
        """
        Parses input text and executes the corresponding command if found.
        Returns the state update if a command was executed, otherwise None.
        """
        if not text.startswith("/"):
            return None

        # Split command from arguments
        parts = text.split(" ", 1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Exact match lookup
        if cmd_name in self._commands:
            return self._commands[cmd_name](args, state, context)

        # Pattern match lookup (e.g., /session1 matches /session)
        # This handles the /session{id} case from the old implementation
        for registered_cmd in self._commands:
            if cmd_name.startswith(registered_cmd) and registered_cmd.startswith("/"):
                # Extract the remaining part as arguments (e.g., "1" from "/session1")
                suffix_args = cmd_name[len(registered_cmd):] + (" " + args if args else "")
                return self._commands[registered_cmd](suffix_args, state, context)

        return None

    def list_commands(self):
        """Returns a list of all registered command names."""
        return list(self._commands.keys())
