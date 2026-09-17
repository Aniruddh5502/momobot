import sys, os, json, subprocess, time, shutil, bootstrap

from pathlib                            import Path
from typing                             import Annotated, Sequence, TypedDict, Dict
from langchain_core.messages            import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph.message            import add_messages, RemoveMessage
from langgraph.graph                    import StateGraph, START, END
from langgraph.prebuilt                 import ToolNode
from prompt_toolkit                     import PromptSession
from prompt_toolkit.key_binding         import KeyBindings
from langchain_ollama                   import ChatOllama
from rich.console                       import Console
from rich.markdown                      import Markdown
from buildSystemPrompt                  import build_system_prompt
from TOOLS.taskState                    import load, Task
from TOOLS.basic_tools                  import base_tools
from TOOLS.subagent_tool                import subagent
from VISUALS.animation                  import ThinkingAnimation
from bootstrap                          import system_prompt, compactionPrompt

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

model               = config["model"]
baseURL             = "http://localhost:11434"
context             = 50000
disableStreaming    = True
reasoning           = False
tokenCount          = 0
recentWindow        = 6
console             = Console()
anim                = ThinkingAnimation()
themeChar           = "✻"

class AgentState(TypedDict):
    messages    :   Annotated[Sequence[BaseMessage], add_messages]
    summary     :   str
    end         :   str
    systemInfo  :   dict
    reasoning   :   bool
    token_usages:   int

def make_session():
    bindings = KeyBindings()
    @bindings.add("escape", "enter")
    def _submit(event):
        event.current_buffer.validate_and_handle()
    @bindings.add("enter")
    def _newline(event):
        event.current_buffer.insert_text("\n")
    return PromptSession(key_bindings=bindings, multiline=True,)

session = make_session()

llm = ChatOllama(
    model="gemma4:31b-cloud",
    reasoning=False,
    base_url="http://localhost:11434",
    num_ctx=100000,
    stream=False,
).bind_tools(tools=base_tools)

llm_think = ChatOllama(
    model="gemma4:31b-cloud",
    reasoning=True,
    base_url="http://localhost:11434",
    num_ctx=100000,
    stream=False,
).bind_tools(tools=base_tools)

def inputNode(state:AgentState)->AgentState:
    isReasoning = state.get("reasoning", False)
    usages = state.get("token_usages",0)
    if state.get("messages"):
        response = state["messages"][-1]
        if isReasoning:
            rawThinking = response.additional_kwargs.get("reasoning_content")
            console.print(f"{themeChar} Thinking..\n")
            console.print(Markdown(str(response.content)))
        console.print(Markdown(str(response.content)))
        columns, lines = shutil.get_terminal_size(fallback=(80,24))
        gap = max(0, columns-21)
        console.print("\n"," "*gap, f"[dim]Token Usages: {usages}[/dim]")
    # Input taking
    console.rule(style="dim")
    user_input = session.prompt("❯  ").strip()
    console.rule(style="dim")
    
    # Exit criteria
    if (not user_input or user_input.lower() in {"x", "c", "exit", "quit", "end"}):
        if user_input:
            console.print(f"{themeChar} Bye...")
        return {"end": "end_loop"}
    # Thinking setup
    reasoning_mode = False
    if "/think" in user_input:
        user_input = user_input.replace("/think","").strip()
        reasoning_mode = True
    return {
        "messages": [HumanMessage(content=user_input)], 
        "reasoning": reasoning_mode
    }

def shouldContinue1(state:AgentState):
    if state["end"] == "end_loop":
        return "end"
    else:
        return "reasoning"

def reasoningNode(state:AgentState)->AgentState:
    from ollama._types import ResponseError
    global tokenCount
    anim.start()
    # get sumary
    summary =   state.get("summary","")
    taskState:Dict[str, Task]   =   load()
    systemPrompt = build_system_prompt(systemPrompt=system_prompt, summary=summary, taskState=taskState)
    systemPromptMessage = SystemMessage(content=systemPrompt)
    
    for attempt in range(5):
        try:
            if reasoning:
                response = llm_think.invoke([systemPromptMessage] + state["messages"])
            else:
                response = llm.invoke([systemPromptMessage] + state["messages"])
            token_usages = response.response_metadata.get("prompt_eval_count", 0)
            anim.stop()
            return {"messages": [response], "token_usages": token_usages}
        except ResponseError as e:
            if e.status_code == 429:
                anim.stop()
                console.print(f"{themeChar} [bold][x] Ollama cloud usage limit reached. Upgrade at https://ollama.com/upgrade[/bold]")
            if (e.status_code in (500, 502, 503, 504) and attempt<4):
                anim.stop()
                console.print(f"{themeChar} [bold][x] Ollama {e.status_code}, retrying ({attempt + 1}/5)...[/bold]")
                time.sleep(3*(attempt + 1))
            else:
                anim.stop()
                raise

def shouldContinue2(state:AgentState):
    lastMsg = state["messages"][-1]
    if lastMsg.tool_calls:
        return "tools"
    else:
        return "compaction"

def compactionNode(state:AgentState)->AgentState:
    usages = state.get("token_usages",0)
    if usages<context:
        return state
    else:
        anim.start()
        try:
            anim.stop()
            console.print(f"{themeChar} [dim]Triggering compaction.[/dim]")
            messages = list(state.get("messages", []))
            split = max(0, len(messages) - recentWindow)
            toCompress = messages[:split]
            if not toCompress:
                return state
            
            existingSummary = state.get("summary","")
            current_compaction_prompt = compactionPrompt
            if existingSummary:
                current_compaction_prompt += f"\nPrevious summarization:\n{existingSummary}"
            
            anim.start()
            response = llm_think.invoke([SystemMessage(content=current_compaction_prompt)]+toCompress)
            newSummary = response.content
            anim.stop()
            removalList = [RemoveMessage(id=m.id) for m in toCompress if m.id]
            console.print(f"{themeChar} [dim green]Compressed {len(toCompress)} msgs. Kept {len(messages) - len(toCompress)} recent[/dim green]")
            
            
            # Instead of resetting to 0, we estimate a reduction or keep it 
            # for the next reasoningNode to update.
            return {
                "messages": removalList,
                "summary": newSummary,
                "token_usages": 0 # Resetting is acceptable here if we assume the prompt was cleared
            }
        except Exception as e:
            console.print(f"{themeChar} [dim red]Error occured while compacting[/dim red]")
            anim.stop()
            return state


TOOL_NODE = ToolNode(tools=base_tools)
graph = StateGraph(AgentState)
graph.add_node("input",inputNode)
graph.add_node("reasoning",reasoningNode)
graph.add_node("tools",TOOL_NODE)
graph.add_node("compaction",compactionNode)

graph.add_edge(START, "input")
graph.add_conditional_edges(
    "input",
    shouldContinue1,
    {
        "end":END,
        "reasoning":"reasoning",
    }
)
graph.add_conditional_edges(
    "reasoning",
    shouldContinue2,
    {
        "tools":"tools",
        "compaction":"compaction",
    }
)
graph.add_edge("tools","reasoning")
graph.add_edge("compaction","input")

momobot = graph.compile()

def main():
    console.print("\n"*25)
    console.print(f"{themeChar} \\m")
    momobot.invoke({"messages":[],"summary":"","end":"","systemInfo":{},"reasoning":False,"token_usages":0})

if __name__ == "__main__":
    main()