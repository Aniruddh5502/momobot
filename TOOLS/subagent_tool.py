import operator
from typing import Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.markdown import Markdown
from setup import sub_agent_sys_prompt

_console = Console()
_SUB_BULLET = "[cyan]●[/cyan]"
_SUB_NEST = "[dim]  ⎿[/dim]"

MODEL          = "gemma4:31b-cloud"
BASE_URL       = "http://localhost:11434"
CTX_WINDOW     = 256000
MAX_ITERATIONS = 200

class SUBAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

def reasoning_node(state: SUBAgentState, llm_with_tools):
    response = llm_with_tools.invoke(list(state["messages"]))
    return {"messages": [response]}

def route_after_reasoning(state: SUBAgentState) -> str:
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return END
    return "tool_execution"

def build_subagent_graph(llm, tools_list):
    llm_with_tools = llm.bind_tools(tools_list)
    tool_node = ToolNode(tools=tools_list)

    workflow = StateGraph(SUBAgentState)
    workflow.add_node("reasoning", lambda state: reasoning_node(state, llm_with_tools))
    workflow.add_node("tool_execution", tool_node)

    workflow.set_entry_point("reasoning")
    workflow.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {
            END: END,
            "tool_execution": "tool_execution",
        }
    )
    workflow.add_edge("tool_execution", "reasoning")

    return workflow.compile()

@tool
def subagent(task: str) -> str:
    """
    Spawn a subagent to complete a task autonomously.
    arg: Detailed breakdown of the tasks that need to be completed.
    """
    _console.print(f"\n{_SUB_BULLET} [bold cyan]Subagent spawned...[/bold cyan]")
    _console.print(f"{_SUB_NEST} [dim]Task: {task[:200]}...[/dim]")

    from TOOLS.basic_tools import base_tools

    llm = ChatOllama(model=MODEL, base_url=BASE_URL, num_ctx=CTX_WINDOW)
    app = build_subagent_graph(llm, base_tools)

    state: SUBAgentState = {
        "messages": [
            SystemMessage(content=sub_agent_sys_prompt),
            HumanMessage(content=task),
        ]
    }

    try:
        state = app.invoke(state, config={"recursion_limit": MAX_ITERATIONS})
        _console.print("[dim green]Subagent Done[/dim green]")
        
        # subagents response formatting
        response_md = Markdown(state['messages'][-1].content)
        _console.print("[dim bold]SUBAGENT: [/dim bold]")
        _console.print(response_md, style='dim')
        return state["messages"][-1].content
    except Exception as e:
        return f"Subagent Error: {str(e)}"