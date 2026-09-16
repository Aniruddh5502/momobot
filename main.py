import sys, os, json, subprocess, time, shutil
from pathlib import Path


# =============================================================================
#                              VENV BOOTSTRAP
# =============================================================================

def _ensure_venv():
    config_file = Path.home() / ".momobot" / "config.json"

    if not config_file.exists():
        print("Momobot is not initialized. Run: momobot-init")
        sys.exit(1)

    config = json.loads(config_file.read_text())
    venv_dir = Path(config["venv"])

    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
    else:
        venv_python = venv_dir / "bin" / "python"

    if not venv_python.exists():
        print(f"Venv not found at {venv_dir}. Run: momobot-init")
        sys.exit(1)

    # Already running inside the correct venv.
    if Path(sys.executable).resolve() == venv_python.resolve():
        return config

    # Relaunch inside the target venv.
    if sys.platform == "win32":
        # Keep the parent process alive while the child owns the console.
        result = subprocess.run(
            [str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:]
        )
        sys.exit(result.returncode)

    # POSIX process replacement.
    os.execv(
        str(venv_python),
        [
            str(venv_python),
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ],
    )


config = _ensure_venv()


# =============================================================================
#                              EXTERNAL DEPENDENCIES
# =============================================================================

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    ToolMessage,
)

from langgraph.graph.message import add_messages, RemoveMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

from langchain_ollama import ChatOllama

from rich.console import Console
from rich.markdown import Markdown

# =============================================================================
#                              INTERNAL DEPENDENCIES
# =============================================================================

from TOOLS.basic_tools import base_tools
from TOOLS.subagent_tool import subagent
from TOOLS.task_state_tool import _load

from VISUALS.animation import ThinkingAnimation
from VISUALS.print import print_smart

from bootstrap import (
    system_prompt,
    terracota,
    green_oli,
    cyan_blue,
    pink_purp,
)

import bootstrap


# =============================================================================
#                                  VARIABLES
# =============================================================================

SYSTEM_PROMPT = system_prompt
MODEL = config["model"]
BASE_URL = "http://localhost:11434"
CTX_WINDOW = 262144
STREAM = False
REASONING = False
TOKEN_USAGE = 0
COMPACTION_THRESHOLD = 50000
RECENT_WINDOW = 6
console = Console()
anim = ThinkingAnimation()


# =============================================================================
#                                AGENT STATE
# =============================================================================

class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    summary: str
    subagent: Annotated[Sequence[BaseMessage], add_messages]
    end: str
    # -------------------------------------------------------------------------
    # Tool execution observation
    # -------------------------------------------------------------------------
    tool_status: str
    tool_error: str
    tool_observation: str
    # Number of consecutive recovery events.
    recovery_attempts: int


# =============================================================================
#                                  LLM SETUP
# =============================================================================
tools = base_tools + [subagent]

llm = ChatOllama(
    model=MODEL,
    reasoning=False,
    base_url=BASE_URL,
    num_ctx=CTX_WINDOW,
    stream=STREAM,
).bind_tools(tools)

llm_think = ChatOllama(
    model=MODEL,
    reasoning=True,
    base_url=BASE_URL,
    num_ctx=CTX_WINDOW,
    stream=STREAM,
).bind_tools(tools)

# =============================================================================
#                              PROMPT SESSION
# =============================================================================
def make_session():
    bindings = KeyBindings()

    @bindings.add("escape", "enter")
    def _submit(event):
        event.current_buffer.validate_and_handle()

    @bindings.add("enter")
    def _newline(event):
        event.current_buffer.insert_text("\n")

    return PromptSession(
        key_bindings=bindings,
        multiline=True,
    )

session = make_session()


# =============================================================================
#                               GRAPH NODES
# =============================================================================


# -----------------------------------------------------------------------------
# USER INPUT
# -----------------------------------------------------------------------------

def input_node(state: AgentState) -> AgentState:
    global REASONING

    # -------------------------------------------------------------------------
    # Print previous response
    # -------------------------------------------------------------------------

    if state.get("messages"):
        response = state["messages"][-1]

        if REASONING:
            raw_thinking = response.additional_kwargs.get("reasoning_content")
            if raw_thinking:
                thinking = Markdown(raw_thinking)
                console.print("\n\n✻ [dim]Thinking...[/dim]")
                console.print(thinking, style="dim")
                console.print(
                    "Thinking...\n\n",
                    style="dim",
                )

        # Only print actual assistant content.
        if getattr(response, "content", None):
            rs = Markdown(str(response.content))
            console.print(rs)
        console.print("")
        columns, lines = shutil.get_terminal_size(fallback=(80, 24))
        gap = max(0, columns - 21)
        console.print(" " * gap, f"[dim]TOKEN USAGES: {TOKEN_USAGE}[/dim]")

    # -------------------------------------------------------------------------
    # Input
    # -------------------------------------------------------------------------

    console.rule(style="dim")
    user_input = session.prompt("❯  ").strip()
    console.rule(style="dim")
    # -------------------------------------------------------------------------
    # Exit
    # -------------------------------------------------------------------------
    if (
        not user_input
        or user_input.lower()
        in {"x", "c", "exit", "quit", "end"}
    ):
        if user_input:
            console.print("Bye...", style=green_oli )
        return {"end": "end_loop"}

    # -------------------------------------------------------------------------
    # /think mode
    # -------------------------------------------------------------------------
    if "/think" in user_input:
        REASONING = True
        user_input = user_input.replace("/think","").strip()
    else:
        REASONING = False
    return {
        "messages": [HumanMessage(content=user_input)],
        "end": "",
    }


# -----------------------------------------------------------------------------
# USER INPUT ROUTER
# -----------------------------------------------------------------------------

def decision_edge_1(state: AgentState):
    if state.get("end") == "end_loop":
        return "END"

    return "run_loop"


# -----------------------------------------------------------------------------
# REASONING NODE
# -----------------------------------------------------------------------------

def reasoning_node(state: AgentState) -> AgentState:
    from ollama._types import ResponseError

    global TOKEN_USAGE

    anim.start()

    # -------------------------------------------------------------------------
    # Current task state
    # -------------------------------------------------------------------------

    current_plan = _load()

    plain_text = (
        json.dumps(
            current_plan,
            indent=2,
        )
        if current_plan
        else "No active task plan present."
    )
    # -------------------------------------------------------------------------
    # System prompt
    # -------------------------------------------------------------------------
    system_content = (
        SYSTEM_PROMPT
        + f"\n\n"
          f"<current_task_state>\n"
          f"```json\n"
          f"{plain_text}\n"
          f"```\n"
          f"</current_task_state>"
    )

    # -------------------------------------------------------------------------
    # Conversation summary
    # -------------------------------------------------------------------------
    summary = state.get(
        "summary",
        "",
    )

    if summary:
        system_content += (
            "\n\n"
            "<conversation_history>\n"
            f"{summary}\n"
            "</conversation_history>"
        )

    # -------------------------------------------------------------------------
    # Tool observation
    #
    # This is important.
    #
    # The model now knows whether the previous tool execution succeeded,
    # failed, or was incomplete without needing another LLM observer.
    # -------------------------------------------------------------------------

    tool_status = state.get(
        "tool_status",
        "",
    )

    tool_observation = state.get(
        "tool_observation",
        "",
    )

    tool_error = state.get(
        "tool_error",
        "",
    )

    if tool_status:
        system_content += (
            "\n\n"
            "<last_tool_execution>\n"
            f"status: {tool_status}\n"
        )

        if tool_observation:
            system_content += (
                f"observation: {tool_observation}\n"
            )

        if tool_error:
            system_content += (
                f"error: {tool_error}\n"
            )

        system_content += (
            "</last_tool_execution>"
        )

    # -------------------------------------------------------------------------
    # Recovery information
    # -------------------------------------------------------------------------

    recovery_attempts = state.get(
        "recovery_attempts",
        0,
    )

    if recovery_attempts:
        system_content += (
            "\n\n"
            "<recovery_context>\n"
            f"Consecutive recovery events: {recovery_attempts}\n"
            "Do not blindly repeat a failed tool call. "
            "Analyze the failure and choose a different action "
            "when appropriate.\n"
            "</recovery_context>"
        )

    system_prompt_message = SystemMessage(
        content=system_content
    )

    # -------------------------------------------------------------------------
    # Invoke Ollama
    # -------------------------------------------------------------------------

    for attempt in range(5):
        try:
            if REASONING:
                response = llm_think.invoke([system_prompt_message] + list(state["messages"]))
            else:
                response = llm.invoke([system_prompt_message] + list(state["messages"]))

            TOKEN_USAGE = response.response_metadata.get("prompt_eval_count", 0)
            anim.stop()
            return {"messages": [response]}

        # ---------------------------------------------------------------------
        # Ollama errors
        # ---------------------------------------------------------------------
        except ResponseError as e:
            if e.status_code == 429:
                anim.stop()
                console.print(
                    "[bold]"
                    "[x] Ollama cloud usage limit reached. "
                    "Upgrade at https://ollama.com/upgrade"
                    "[/bold]"
                )
                sys.exit(0)
            if (
                e.status_code in
                (500, 502, 503, 504)
                and attempt < 4
            ):
                anim.stop()
                console.print(
                    f"[yellow]"
                    f"⚠ Ollama {e.status_code}, "
                    f"retrying ({attempt + 1}/5)..."
                    f"[/yellow]"
                )
                time.sleep(
                    3 * (attempt + 1)
                )
                anim.start()
            else:
                anim.stop()
                raise
        except Exception:
            anim.stop()
            raise

# -----------------------------------------------------------------------------
# REASONING ROUTER
# -----------------------------------------------------------------------------

def reasoning_edge(state: AgentState):

    messages = list(
        state.get("messages", [])
    )

    if not messages:
        return "compact_check"

    last = messages[-1]

    # The LLM wants to use a tool.
    if getattr(last, "tool_calls", None):
        return "tool"

    # The LLM produced a normal response.
    return "compact_check"


# -----------------------------------------------------------------------------
# PRE-TOOL NODE
#
# This is intentionally deterministic.
#
# ToolNode already validates and dispatches tools. This node exists as the
# control point where you can later add permission checks, argument validation,
# logging, or tool-specific policies without changing the graph.
# -----------------------------------------------------------------------------

def pre_tool_node(state: AgentState) -> AgentState:

    messages = list(
        state.get("messages", [])
    )

    if not messages:
        return state

    last = messages[-1]

    tool_calls = getattr(
        last,
        "tool_calls",
        [],
    )

    if not tool_calls:
        return state

    # Reset the previous observation because a new tool execution is starting.
    return {
        "tool_status": "executing",
        "tool_error": "",
        "tool_observation": (
            f"Executing {len(tool_calls)} tool call(s)."
        ),
    }


# -----------------------------------------------------------------------------
# OBSERVER NODE
#
# Deterministic post-tool inspection.
#
# It does NOT ask another LLM whether the tool worked.
# It uses ToolMessage status/error information supplied by LangChain.
# -----------------------------------------------------------------------------

def observe_node(state: AgentState) -> AgentState:

    messages = list(
        state.get("messages", [])
    )

    if not messages:
        return {
            "tool_status": "unknown",
            "tool_error": "",
            "tool_observation": "No messages available.",
        }

    # -------------------------------------------------------------------------
    # Collect the most recent consecutive ToolMessages.
    #
    # ToolNode may execute multiple tool calls in one pass.
    # -------------------------------------------------------------------------

    tool_messages = []

    for message in reversed(messages):

        if isinstance(message, ToolMessage):
            tool_messages.append(message)

        else:
            break

    tool_messages.reverse()

    if not tool_messages:
        return {
            "tool_status": "unknown",
            "tool_error": "",
            "tool_observation": (
                "No ToolMessage was produced."
            ),
        }

    # -------------------------------------------------------------------------
    # Inspect results
    # -------------------------------------------------------------------------

    errors = []

    for message in tool_messages:

        status = getattr(
            message,
            "status",
            None,
        )

        if status == "error":

            errors.append(
                str(
                    getattr(
                        message,
                        "content",
                        "Unknown tool error",
                    )
                )
            )

    # -------------------------------------------------------------------------
    # Failure
    # -------------------------------------------------------------------------

    if errors:

        error_text = "\n".join(errors)

        return {
            "tool_status": "failure",
            "tool_error": error_text,
            "tool_observation": (
                f"{len(errors)} tool call(s) failed."
            ),
        }

    # -------------------------------------------------------------------------
    # Success
    # -------------------------------------------------------------------------

    tool_names = []

    for message in tool_messages:

        name = getattr(
            message,
            "name",
            None,
        )

        if name:
            tool_names.append(name)

    if tool_names:

        observation = (
            "Tool execution completed successfully. "
            "Executed: "
            + ", ".join(tool_names)
        )

    else:

        observation = (
            "Tool execution completed successfully."
        )

    return {
        "tool_status": "success",
        "tool_error": "",
        "tool_observation": observation,
    }


# -----------------------------------------------------------------------------
# OBSERVER ROUTER
# -----------------------------------------------------------------------------

def observation_edge(state: AgentState):

    status = state.get(
        "tool_status",
        "unknown",
    )

    if status == "failure":
        return "recovery"

    if status == "partial":
        return "reasoning"

    return "reasoning"


# -----------------------------------------------------------------------------
# RECOVERY NODE
#
# This does NOT automatically repeat the failed tool.
#
# Instead it gives the reasoning node explicit recovery context so the model
# can inspect the error and decide what should happen next.
# -----------------------------------------------------------------------------

def recovery_node(state: AgentState) -> AgentState:

    attempts = state.get(
        "recovery_attempts",
        0,
    )

    attempts += 1

    error = state.get(
        "tool_error",
        "Unknown tool error.",
    )

    console.print(
        "\n[bold yellow]⚠ Tool execution failed[/bold yellow]"
    )

    console.print(
        f"[yellow]{error}[/yellow]"
    )

    # -------------------------------------------------------------------------
    # Prevent recovery counter from growing forever.
    #
    # We still send the problem back to reasoning. The model can decide to
    # abandon, change approach, or retry with corrected arguments.
    # -------------------------------------------------------------------------

    return {
        "recovery_attempts": attempts,
        "tool_status": "failure",
        "tool_observation": (
            "The previous tool execution failed. "
            "The next reasoning step must analyze the error "
            "before attempting another action."
        ),
    }


# -----------------------------------------------------------------------------
# COMPACTION CHECK
#
# This is separate from the "does the model want a tool?" decision.
#
# Your old graph used "no tool call" == "compact", which meant the graph's
# control flow conceptually mixed two unrelated decisions.
# -----------------------------------------------------------------------------

def compaction_check_edge(state: AgentState):

    if TOKEN_USAGE >= COMPACTION_THRESHOLD:
        return "compact"

    return "input"


# -----------------------------------------------------------------------------
# COMPACTION NODE
# -----------------------------------------------------------------------------

def compaction_node(state: AgentState) -> AgentState:

    global TOKEN_USAGE

    if TOKEN_USAGE < COMPACTION_THRESHOLD:
        return {}

    anim.start()

    console.print(
        "● Triggering Compaction",
        style=cyan_blue,
    )

    messages = list(
        state.get("messages", [])
    )

    split = max(
        0,
        len(messages) - RECENT_WINDOW,
    )

    to_compress = messages[:split]

    # -------------------------------------------------------------------------
    # Nothing to compress
    # -------------------------------------------------------------------------

    if not to_compress:

        anim.stop()

        return {}

    # -------------------------------------------------------------------------
    # Existing summary
    # -------------------------------------------------------------------------

    existing_summary = state.get(
        "summary",
        "",
    )

    if existing_summary:

        summary_instruction = (
            "You are the Context Compactor. "
            "Below is the running summary so far, "
            "followed by new conversation messages. "
            "Extend the summary to incorporate the new messages. "
            "Preserve: technical decisions, key constraints, "
            "current goals, and user preferences. "
            "Discard fluff. Be concise.\n\n"
            f"Running summary:\n{existing_summary}"
        )

    else:

        summary_instruction = (
            "You are the Context Compactor. "
            "Summarize the provided conversation into a dense "
            "'Session State Summary'. "
            "Preserve: technical decisions, key constraints, "
            "current goals, and user preferences. "
            "Discard conversational fluff and repetitive logs. "
            "Be concise."
        )

    # -------------------------------------------------------------------------
    # Dedicated compaction model
    # -------------------------------------------------------------------------

    bare_llm = ChatOllama(
        model=MODEL,
        base_url=BASE_URL,
        num_ctx=CTX_WINDOW,
    )

    response = bare_llm.invoke(
        [
            SystemMessage(
                content=summary_instruction
            )
        ]
        + to_compress
    )

    new_summary = response.content

    # -------------------------------------------------------------------------
    # Remove old messages
    # -------------------------------------------------------------------------

    removal_list = [
        RemoveMessage(id=m.id)
        for m in to_compress
        if m.id
    ]

    console.print(
        f"[dim green]"
        f"Compressed {len(to_compress)} msgs, "
        f"kept {len(messages) - len(to_compress)} recent."
        f"[/dim green]"
    )

    anim.stop()

    # Reset token counter after compaction.
    TOKEN_USAGE = 0

    return {
        "summary": new_summary,
        "messages": removal_list,
    }


# =============================================================================
#                               GRAPH BUILD
# =============================================================================

graph = StateGraph(AgentState)


# -----------------------------------------------------------------------------
# Tool executor
# -----------------------------------------------------------------------------

TOOL_NODE = ToolNode(
    tools=tools
)


# -----------------------------------------------------------------------------
# Register nodes
# -----------------------------------------------------------------------------

graph.add_node(
    "USER_INPUT",
    input_node,
)

graph.add_node(
    "REASONING",
    reasoning_node,
)

graph.add_node(
    "PRE_TOOL",
    pre_tool_node,
)

graph.add_node(
    "TOOL_NODE",
    TOOL_NODE,
)

graph.add_node(
    "OBSERVE",
    observe_node,
)

graph.add_node(
    "RECOVERY",
    recovery_node,
)

graph.add_node(
    "COMPACT",
    compaction_node,
)


# =============================================================================
#                               GRAPH EDGES
# =============================================================================


# -----------------------------------------------------------------------------
# START → USER INPUT
# -----------------------------------------------------------------------------

graph.add_edge(
    START,
    "USER_INPUT",
)


# -----------------------------------------------------------------------------
# USER INPUT
#
# Exit → END
# Otherwise → REASONING
# -----------------------------------------------------------------------------

graph.add_conditional_edges(
    "USER_INPUT",
    decision_edge_1,
    {
        "END": END,
        "run_loop": "REASONING",
    },
)


# -----------------------------------------------------------------------------
# REASONING
#
# Tool call → PRE_TOOL
# Normal answer → COMPACTION_CHECK
# -----------------------------------------------------------------------------

graph.add_conditional_edges(
    "REASONING",
    reasoning_edge,
    {
        "tool": "PRE_TOOL",
        "compact_check": "COMPACT_CHECK",
    },
)


# -----------------------------------------------------------------------------
# COMPACTION CHECK
#
# This is implemented as a conditional edge directly from a synthetic node.
# To keep the graph explicit, we add a tiny passthrough node.
# -----------------------------------------------------------------------------

def compaction_check_node(state: AgentState) -> AgentState:
    return {}


graph.add_node(
    "COMPACT_CHECK",
    compaction_check_node,
)


graph.add_conditional_edges(
    "COMPACT_CHECK",
    compaction_check_edge,
    {
        "compact": "COMPACT",
        "input": "USER_INPUT",
    },
)


# -----------------------------------------------------------------------------
# PRE_TOOL → TOOL_NODE
# -----------------------------------------------------------------------------

graph.add_edge(
    "PRE_TOOL",
    "TOOL_NODE",
)


# -----------------------------------------------------------------------------
# TOOL_NODE → OBSERVE
# -----------------------------------------------------------------------------

graph.add_edge(
    "TOOL_NODE",
    "OBSERVE",
)


# -----------------------------------------------------------------------------
# OBSERVE
#
# Success / partial → REASONING
# Failure → RECOVERY
# -----------------------------------------------------------------------------

graph.add_conditional_edges(
    "OBSERVE",
    observation_edge,
    {
        "reasoning": "REASONING",
        "recovery": "RECOVERY",
    },
)


# -----------------------------------------------------------------------------
# RECOVERY → REASONING
# -----------------------------------------------------------------------------

graph.add_edge(
    "RECOVERY",
    "REASONING",
)


# -----------------------------------------------------------------------------
# COMPACT → USER INPUT
# -----------------------------------------------------------------------------

graph.add_edge(
    "COMPACT",
    "USER_INPUT",
)


# =============================================================================
#                                COMPILE GRAPH
# =============================================================================

momobot = graph.compile()


# =============================================================================
#                                    MAIN
# =============================================================================

def main():

    console.print(
        "\n" * 25
    )

    console.print(
        "[●_●]",
        style=terracota,
    )

    momobot.invoke(
        {
            "messages": [],
            "summary": "",
            "subagent": [],
            "end": "",

            "tool_status": "",
            "tool_error": "",
            "tool_observation": "",

            "recovery_attempts": 0,
        }
    )


# =============================================================================
#                              PROGRAM ENTRY
# =============================================================================

if __name__ == "__main__":
    main()