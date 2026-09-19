from typing import Any, Optional, Dict, TypedDict

class ToolResponse(TypedDict):
    status: str
    data: Any
    error_code: Optional[str]
    error_message: Optional[str]
    recovery_hint: Optional[str]
    metadata: Optional[Dict[str, Any]]

def create_tool_response(
    status: str,
    data: Any = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    recovery_hint: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> ToolResponse:
    """
    Standardizes tool outputs to ensure the agent receives consistent data structures.
    """
    return {
        "status": status,
        "data": data,
        "error_code": error_code,
        "error_message": error_message,
        "recovery_hint": recovery_hint,
        "metadata": metadata
    }
