
# =============================================================================
#                             EXTERNAL DEPENDENCIES                           |                 
# =============================================================================
from typing                     import Annotated, Sequence, TypedDict
from langchain_core.messages    import BaseMessage, SystemMessage
from langchain_core.messages    import HumanMessage
from langgraph.graph.message    import add_messages, RemoveMessage
from langgraph.graph            import StateGraph, START, END
from prompt_toolkit             import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from langgraph.prebuilt         import ToolNode
from langchain_ollama           import ChatOllama
from rich.console               import Console
from rich.markdown              import Markdown
# =============================================================================
#                             INTERNAL DEPENDENCIES                           |                 
# =============================================================================
from TOOLS.basic_tools          import base_tools
from TOOLS.subagent_tool        import subagent
from TOOLS.task_state_tool      import _load
from VISUALS.animation          import ThinkingAnimation
from VISUALS.print              import print_smart
from setup                      import system_prompt, terracota, green_oli, cyan_blue, pink_purp
import json
import setup

# =============================================================================
#                                  VARIABLES                                  |
# =============================================================================
SYSTEM_PROMPT           =   system_prompt
MODEL                   =   "gemma4:31b-cloud"
BASE_URL                =   "http://localhost:11434"
CTX_WINDOW              =   262144
STREAM                  =   False
REASONING               =   False
TOKEN_USAGE             =   0
COMPACTION_THRESHOLD    =   100000
RECENT_WINDOW           =   6
console                 =   Console()
anim                    =   ThinkingAnimation()

# =============================================================================
#                               STATE DEFINITION                              |
# =============================================================================
class AgentState(TypedDict):
    messages : Annotated[Sequence[BaseMessage], add_messages]
    summary  : str
    subagent : Annotated[Sequence[BaseMessage], add_messages]
    end      : str

# =============================================================================
#                                  LLM SETUP                                  |
# =============================================================================
tools = base_tools + [subagent]

llm             = ChatOllama(model=MODEL, reasoning = False, base_url = BASE_URL, num_ctx = CTX_WINDOW, stream      =   STREAM).bind_tools(tools)

llm_think       = ChatOllama(model = MODEL, reasoning = True, base_url = BASE_URL, num_ctx = CTX_WINDOW, stream = STREAM).bind_tools(tools)


def make_session():
    bindings = KeyBindings()

    @bindings.add("escape", "enter")
    def _submit(event):
        event.current_buffer.validate_and_handle()

    @bindings.add("enter")
    def _newline(event):
        event.current_buffer.insert_text("\n")

    return PromptSession(key_bindings=bindings, multiline=True)

session = make_session()

# =============================================================================
#                               GRAPH NODES DEF                               |
# =============================================================================
# USER INPUT
def input_node(state:AgentState)-> AgentState:
    global REASONING
    # Previous runs response
    if state['messages']:
        response    = state['messages'][-1]

        if REASONING == True:
            thinking    = Markdown(response.additional_kwargs.get('reasoning_content'))
            console.print("\n\n✻ ","[dim]Thinking...[/dim]")
            console.print(thinking, style='dim')
            console.print("Thinking...\n\n", style='dim')
        rs          = Markdown(response.content)
        console.print(rs)
        
        console.print("")
        console.print("[dim green]                                                                            ● TOKEN USAGES: [/dim green]", f"[dim green]{TOKEN_USAGE}[/dim green]")

    console.rule(style='dim')
    user_input = session.prompt("❯  ").strip()
    console.rule(style='dim')

    # ----------------------------------------------------------------------
    # tags
    # ----------------------------------------------------------------------
    if not user_input or user_input.lower() in {"x","c","exit","quit","end"}:
        if user_input:
            console.print("Bye...",style=green_oli)
        return {'end' :"end_loop"}
    
    if "/think" in user_input:
        REASONING = True
        user_input = user_input.replace("/think", "").strip()
    else:
        REASONING = False
    input = HumanMessage(content=user_input)    
    return {'messages':input}

# END or CONVERSATION
def descision_edge_1(state:AgentState):
    end_or_not = state['end']
    if end_or_not == "end_loop":
        return "END"
    return "run_loop"

# REASONING NODE
def reasoning_node(state: AgentState) -> AgentState:
    anim.start()
    CURRENT_PLAN   = _load()
    PLAIN_TEXT     = json.dumps(CURRENT_PLAN, indent=2) if CURRENT_PLAN else "No active task plan present."
    SYSTEM_CONTENT = (SYSTEM_PROMPT + f"\n\n<current_task_state>\n\n```json{PLAIN_TEXT}\n\n</current_task_state>```")
    summary        = state.get('summary', "")
    if summary:
        SYSTEM_CONTENT += f"\n\n<conversation_history>\n\n{summary}\n\n</conversation_history>"
    System_prompt  = SystemMessage(content=SYSTEM_CONTENT)

    import time
    from ollama._types import ResponseError

    for attempt in range(5):
        try:
            if REASONING == True:
                response = llm_think.invoke([System_prompt] + list(state["messages"]))
            else:
                response = llm.invoke([System_prompt] + list(state["messages"]))
            
            global TOKEN_USAGE
            TOKEN_USAGE = response.response_metadata.get("prompt_eval_count", 0)
            anim.stop()
            return {'messages': [response]}
        except ResponseError as e:
            if e.status_code in (500, 502, 503, 504) and attempt < 4:
                anim.stop()
                console.print(f"[yellow]⚠ Ollama {e.status_code}, retrying ({attempt+1}/5)...[/yellow]")
                time.sleep(3 * (attempt + 1))
                anim.start()
            else:
                anim.stop()
                raise
        except Exception:
            anim.stop()
            raise


# COMPACTION NODE
def compaction_node(state:AgentState)-> AgentState:
    global TOKEN_USAGE
    if TOKEN_USAGE < COMPACTION_THRESHOLD:
        return state
    anim.start()
    console.print("● Triggering Compaction", style=cyan_blue)
    messages        =   list(state['messages'])
    split           =   max(0, len(messages) - RECENT_WINDOW)
    to_compress     =   messages[:split]
    if not to_compress:
        return state
    existing_summary        =   state.get("summary","")
    if existing_summary:
        summary_instruction = (
            "You are the Context Compactor. Below is the running summary so far, "
            "followed by new conversation messages. Extend the summary to incorporate "
            "the new messages. Preserve: technical decisions, key constraints, current "
            "goals, and user preferences. Discard fluff. Be concise.\n\n"
            f"Running summary:\n{existing_summary}"
        )
    else:
        summary_instruction = (
            "You are the Context Compactor. Summarize the provided conversation "
            "into a dense 'Session State Summary'. Preserve: technical decisions, "
            "key constraints, current goals, and user preferences. "
            "Discard conversational fluff and repetitive logs. Be concise."
        )
    bare_llm            = ChatOllama(model=MODEL, base_url=BASE_URL, num_ctx=CTX_WINDOW)
    response            = bare_llm.invoke([SystemMessage(content=summary_instruction)] + to_compress)
    new_summary         = response.content
    removal_list         = [RemoveMessage(id=m.id) for m in to_compress if m.id]
    console.print(f"[dim green]Compressed {len(to_compress)} msgs, kept {len(messages) - len(to_compress)} recent.[/dim green]")
    anim.stop()   
    return {"summary": new_summary, "messages": removal_list}


def descision_edge(state:AgentState):
    last = state['messages'][-1]
    if not last.tool_calls:
        return "compact"
    return "continue"

# Graph Build
graph     = StateGraph(AgentState)
TOOL_NODE = ToolNode(tools=tools)
graph.add_node("USER_INPUT", input_node)
graph.add_node("REASONING", reasoning_node)
graph.add_node("TOOL_NODE", TOOL_NODE)
graph.add_node("COMPACT",   compaction_node)
graph.add_edge(START, "USER_INPUT")
graph.add_conditional_edges(
    "USER_INPUT",
    descision_edge_1,
    {
        "END":END,
        "run_loop":"REASONING",
    }
)
graph.add_conditional_edges(
    "REASONING",
    descision_edge,
    {
        "continue": "TOOL_NODE",
        "compact":  "COMPACT",
    },
)
graph.add_edge("TOOL_NODE", "REASONING")
graph.add_edge("COMPACT", "USER_INPUT")
agent = graph.compile()

if __name__ == "__main__":
    console.print("\n"*25)
    console.print("[●_●]",style=terracota)
    agent.invoke({"messages": [], "summary": "", "end": ""})
