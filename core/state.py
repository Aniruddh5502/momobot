from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    summary: str
    end: str
    systemInfo: dict
    reasoning: bool
    token_usages: int
    last_action: str


def get_default_state() -> AgentState:
    return {
        "messages": [],
        "summary": "",
        "end": "",
        "systemInfo": {},
        "reasoning": False,
        "token_usages": 0,
        "last_action": "init",
    }