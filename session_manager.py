import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, RemoveMessage, ToolMessage

try:
    from bootstrap import CONVERSATION_DIR
except ImportError:
    CONVERSATION_DIR = Path("CONVERSATION")

class SessionEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BaseMessage):
            return {
                "type": obj.__class__.__name__,
                "content": obj.content,
                "additional_kwargs": getattr(obj, "additional_kwargs", {}),
                "id": getattr(obj, "id", None),
                "tool_call_id": getattr(obj, "tool_call_id", None),
                "status": getattr(obj, "status", None)
            }
        return super().default(obj)

def message_decoder(dct):
    if "type" in dct and dct["type"] in ["HumanMessage", "AIMessage", "SystemMessage", "RemoveMessage", "ToolMessage"]:
        msg_cls = globals().get(dct["type"])
        if msg_cls:
            if dct["type"] == "ToolMessage":
                msg = msg_cls(
                    content=dct.get("content", ""), 
                    tool_call_id=dct.get("tool_call_id", ""),
                    status=dct.get("status", "success")
                )
            else:
                msg = msg_cls(
                    content=dct.get("content", ""), 
                    additional_kwargs=dct.get("additional_kwargs", {})
                )
            if dct.get("id"):
                msg.id = dct["id"]
            return msg
    return dct

class SessionManager:
    def __init__(self):
        self.sessions_dir = Path(CONVERSATION_DIR) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_name: str) -> Path:
        safe_name = "".join([c for c in session_name if c.isalnum() or c in (" ", "_", "-")]).strip()
        if not safe_name:
            safe_name = "unnamed_session"
        return self.sessions_dir / f"{safe_name}.json"

    def save_session(self, session_name: str, state: Dict[str, Any]):
        path = self._get_session_path(session_name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, cls=SessionEncoder)

    def load_session(self, session_name: str) -> Optional[Dict[str, Any]]:
        path = self._get_session_path(session_name)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f, object_hook=message_decoder)

    def list_sessions(self, limit: int = 10) -> List[str]:
        sessions = list(self.sessions_dir.glob("*.json"))
        sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return [p.stem for p in sessions[:limit]]

    def delete_session(self, session_name: str) -> bool:
        path = self._get_session_path(session_name)
        if path.exists():
            path.unlink()
            return True
        return False
