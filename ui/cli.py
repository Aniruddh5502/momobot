import sys
import shutil, json
import logging
import uuid
from typing import Optional, Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.markup import escape
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, ToolMessage
from bootstrap import config
from core.engine import MomobotAgent
from core.state import AgentState
from cmd.registry import CommandRegistry, CommandResult
from cmd.session_cmds import register_session_commands, register_session_name

# Set up professional logging for the UI layer
logger = logging.getLogger("momobot.ui.cli")

theme_char      =   "✽"
book_cloth      =   "#CC785C"
error           =   "#BF4D43"
focus           =   "#61AAF2"
white           =   "#FFFFFF"
black           =   "#000000"
cloud_light     =   "#BFBFBA"


class MomobotInterface:
    """
    Production-grade CLI Interface for Momobot.
    Handles user input, session state management, and formatted output.
    """
    def __init__(self, agent: MomobotAgent, config: Dict[str, Any]):
        self.agent = agent
        self.config = config
        self.console = Console()
        self.registry = CommandRegistry()
        register_session_commands(self.registry)

        self.theme_char = config.get("theme_char", "✽")
        self.ai_response = "⬤"
        self.session = self._make_session()

        # The thread_id is the key for LangGraph persistence
        self.current_thread_id = str(uuid.uuid4())[:8]

        # State is now partially managed by the checkpointer,
        # but we keep a local mirror for UI responsiveness
        self.state: AgentState = self._initialize_state()

        # Track message indices to avoid re-printing history
        self._last_printed_index = 0

    def _initialize_state(self) -> AgentState:
        """Creates a clean starting state for the agent."""
        return {
            "messages": [],
            "summary": "",
            "end": "",
            "systemInfo": {},
            "reasoning": False,
            "token_usages": 0,
            "last_action": "init"
        }

    def _make_session(self) -> PromptSession:
        """Configures the prompt toolkit session with production keybindings."""
        bindings = KeyBindings()
        @bindings.add("escape", "enter")
        def _submit(event):
            event.current_buffer.validate_and_handle()
        @bindings.add("enter")
        def _newline(event):
            event.current_buffer.insert_text("\n")
        return PromptSession(key_bindings=bindings, multiline=True)

    def _render_message(self, message: BaseMessage):

        if isinstance(message, HumanMessage):
            self.console.print(" ")
            self.console.rule(style="dim")
            self.console.print(
                f"[bold {book_cloth}]❯[/bold {book_cloth}] "
                f"[bold]{escape(message.content)}[/bold]"
            )
            self.console.rule(style="dim")

        elif isinstance(message, AIMessage):
            reasoning = message.additional_kwargs.get("reasoning_content")
            if reasoning:
                self.console.print(Panel(
                    escape(reasoning),
                    title=f"[{self.ai_response}] Reasoning",
                    title_align="left",
                    border_style="dim",
                    style="italic dim",
                ))

            if message.content:
                self.console.print("")
                self.console.print(f"{self.ai_response} ", end="")
                self.console.print(Markdown(message.content))
                self.console.print("")

            
        elif isinstance(message, ToolMessage):
            self._render_tool_result(message)

    def _render_tool_result(self, message):
        """Render a ToolMessage using the standardized create_tool_response shape."""
        name = getattr(message, "name", None) or "tool"

        # --- Normalize content (str, list of content blocks, or other) ---
        content = message.content
        if isinstance(content, list):
            content = "\n".join(
                b.get("text", "") if isinstance(b, dict) else str(b)
                for b in content
            )
        elif not isinstance(content, str):
            content = str(content)

        # --- Parse the create_tool_response payload ---
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = None

        if not isinstance(parsed, dict) or "status" not in parsed:
            # Fallback for unstructured results: one-line preview.
            preview = content.replace("\n", " ").strip()
            if len(preview) > 100:
                preview = preview[:100].rstrip() + "…"
            self.console.print(
                f"{theme_char} [dim]{name}[/dim]  [dim]{escape(preview)}[/dim]"
            )
            return

        # --- Extract the fields we care about ---
        status     = parsed.get("status", "success")
        error_code = parsed.get("error_code")
        error_msg  = parsed.get("error_message")
        hint       = parsed.get("recovery_hint")
        meta       = parsed.get("metadata") or {}

        marker = {"success": "✓", "warning": "!", "error": "✗"}.get(status, "·")
        color  = {"success": "green", "warning": "yellow", "error": "red"}.get(status, "dim")

        # --- One-line summary ---
        # Priority: state_delta (what the tool did) > error_message > nothing
        summary = meta.get("state_delta") or error_msg
        if summary:
            summary = str(summary).replace("\n", " ").strip()
            if len(summary) > 120:
                summary = summary[:120].rstrip() + "…"

        header = f"{theme_char} [dim]{name}[/dim]  [{color}]{marker}[/{color}]"
        if summary:
            header += f"  [dim]{escape(summary)}[/dim]"
        self.console.print(header)

        # --- Extra detail on failure ---
        if status in ("error", "warning"):
            if error_code and str(error_code) not in (summary or ""):
                self.console.print(
                    f"     [dim]code:[/dim] [{color}]{escape(str(error_code))}[/{color}]"
                )
            if error_msg and str(error_msg) not in (summary or ""):
                self.console.print(f"     [dim]msg:[/dim]  {escape(str(error_msg))}")
            if hint:
                self.console.print(
                    f"     [dim]hint:[/dim] [yellow]{escape(str(hint))}[/yellow]"
                )

            color = {"success": "green", "warning": "yellow", "error": "red"}.get(status, "dim")
            name = getattr(message, "name", None) or "tool"
            self.console.print(f"{theme_char} [dim]{name}[/dim]  result  [{color}]{status}[/{color}]")

    def display_updates(self, state: AgentState, show_footer: bool = False):
        """
        Analyzes the state and prints only the new messages
        generated since the last update.
        """
        messages = state.get("messages", [])

        for i in range(self._last_printed_index, len(messages)):
            self._render_message(messages[i])
            self._last_printed_index = i + 1

        if not show_footer:
            return

        usages = state.get("token_usages", 0)
        cols, _ = shutil.get_terminal_size(fallback=(80, 24))
        footer = f"[dim]Token Usages: {usages}[/dim]"
        self.console.print(f"\n{' ' * (cols - len(footer))} {footer}")

    def handle_input(self, user_input: str) -> Optional[bool]:
        user_input = user_input.strip()
        if not user_input:
            return True

        if user_input.lower() in {"x", "c", "exit", "quit", "end"}:
            try:
                self.agent.app.update_state(
                    {"configurable": {"thread_id": self.current_thread_id}},
                    self.state,
                )
                # Make sure the session appears in /sessions even if it never
                # got a chance to register (e.g. user exits before first reply).
                register_session_name(self.current_thread_id, user_input)
                self.console.print(
                    f"{self.theme_char} [dim]Session {self.current_thread_id} saved.[/dim]"
                )
            except Exception as e:
                self.console.print(f"[dim red]Could not save session: {e}[/dim red]")

            self.console.print(f"{self.theme_char} [bold]Shutting down...[/bold]")
            return False

        # --- Slash commands ---
        cmd_result: Optional[CommandResult] = self.registry.execute(
            user_input, self.state, {"ui": self}
        )
        if cmd_result is not None:
            if cmd_result.state is not None:
                self.state = cmd_result.state
            if cmd_result.render:
                self._last_printed_index = 0
                self.display_updates(self.state)          # no footer on replay
            else:
                # Skip anything already in state (avoid re-printing history).
                self._last_printed_index = len(self.state.get("messages", []))
            return True

        # --- Regular chat: hand off to the agent ---

        # Register/refresh session name based on the first 50 chars of the
        # first user message. Safe to call every turn — it only sets the
        # name once and bumps `updated_at` thereafter.
        register_session_name(self.current_thread_id, user_input)

        reasoning_mode = False
        if "/think" in user_input:
            user_input = user_input.replace("/think", "").strip()
            reasoning_mode = True

        self.state["messages"] = self.state.get("messages", [])
        self.state["messages"].append(HumanMessage(content=user_input))
        self.state["reasoning"] = reasoning_mode
        self.state["last_action"] = "input"

        self._last_printed_index = len(self.state["messages"])

        try:
            for event in self.agent.run(
                self.state,
                thread_id=self.current_thread_id,
            ):
                self.state = event
                self.display_updates(self.state)                 # stream, no footer

            self.display_updates(self.state, show_footer=True)   # footer, once
        except Exception as e:
            logger.exception("Error during agent execution")
            self.console.print(f"[bold red]Critical Error:[/bold red] {escape(str(e))}")
            self.console.print("[dim]Please check logs for details.[/dim]")

        return True

    def run(self):
        """Main execution loop for the CLI."""
        print("\n" * 10)
        from config import config
        self.console.print(Panel(
            f"""\n            {self.theme_char} \\  [dim]Type 'exit' or 'quit' to leave.[/dim]\n            \n\n                Model: {config['model']} """,
            title="Momobot",
            title_align="left",
            border_style=f"{book_cloth}",
            height=8,
        ))
        print("\n" * 5)

        while True:
            try:
                self.console.rule(style="dim")
                user_input = self.session.prompt("❯  ").strip()
                self.console.rule(style="dim")
            except KeyboardInterrupt:
                self.console.rule(style="dim")
                try:
                    self.console.print(f"\n{theme_char} Exiting..\n")
                except Exception as e:
                    self.console.print(f"\n[dim red]Could not save session: {e}[/dim red]")
                break

            if not self.handle_input(user_input):
                self.console.rule(style="dim")
                break


def main():
    import bootstrap
    from core.engine import MomobotAgent

    config = bootstrap.config
    agent = MomobotAgent(config)
    interface = MomobotInterface(agent, config)
    interface.run()


if __name__ == "__main__":
    main()