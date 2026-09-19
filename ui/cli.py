import sys
import shutil
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
from cmd.registry import CommandRegistry
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

        # ---- Human turn ----
        if isinstance(message, HumanMessage):
            self.console.print(" ")
            self.console.rule(style="dim")
            self.console.print(
                f"[bold {book_cloth}]❯[/bold {book_cloth}] "
                f"[bold]{escape(message.content)}[/bold]"
            )
            self.console.rule(style="dim")

        # ---- AI turn (may contain reasoning, text, and/or tool calls) ----
        elif isinstance(message, AIMessage):
            reasoning = message.additional_kwargs.get("reasoning_content")
            if reasoning:
                self.console.print(f"\n\n{theme_char} Thinking...\n")
                self.console.print(Panel(
                    escape(reasoning),
                    title=f"[{self.theme_char}] Reasoning",
                    title_align="left",
                    border_style="dim",
                    style="italic dim",
                ))

            if message.content:
                self.console.print("")
                self.console.print(f"{theme_char} ",end="")
                self.console.print(Markdown(message.content))
                self.console.print("")

            # Tool calls the model requested on this turn
            for call in (getattr(message, "tool_calls", None) or []):
                name = call.get("name", "tool")
                args = call.get("args", {})
                preview = self._format_args(args)
                self.console.print(
                    f"\n{theme_char} [dim]{name}[/dim][dim]({preview})[/dim]"
                )

        # ---- Tool result ----
        elif isinstance(message, ToolMessage):
            name = getattr(message, "name", None) or "tool"
            status = getattr(message, "status", "success")
            content = message.content if isinstance(message.content, str) else str(message.content)

            # Tool responses are the structured dicts from create_tool_response.
            # Show a compact one-liner plus a short preview of the payload.
            preview = self._truncate(content, 200)
            marker = "✓" if status == "success" else "✗"
            color = "dim" if status == "success" else "red"

            self.console.print(
                f"\n[{color}]  {marker}  {name}:[/{color}] "
                f"[dim]{escape(preview)}[/dim]"
            )

    @staticmethod
    def _format_args(args: dict) -> str:
        """Compact, single-line rendering of a tool call's args."""
        if not isinstance(args, dict):
            return str(args)[:80]
        parts = []
        for k, v in args.items():
            s = str(v).replace("\n", " ")
            if len(s) > 40:
                s = s[:40] + "…"
            parts.append(f"{k}={s}")
        return ", ".join(parts)

    @staticmethod
    def _truncate(s: str, n: int) -> str:
        s = s.replace("\n", " ")
        return s if len(s) <= n else s[:n] + "…"
        
    def display_updates(self, state: AgentState):
        """
        Analyzes the state and prints only the new messages 
        generated since the last update.
        """
        messages = state.get("messages", [])
        
        for i in range(self._last_printed_index, len(messages)):
            self._render_message(messages[i])
            self._last_printed_index = i + 1
        
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
                self.display_updates(self.state)
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

            self.display_updates(self.state)
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
