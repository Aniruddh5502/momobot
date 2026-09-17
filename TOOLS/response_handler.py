from typing import Any, Optional, Dict, Union

def create_tool_response(
    status: str = "success", 
    data: Any = None, 
    metadata: Optional[Dict[str, Any]] = None, 
    error_code: Optional[str] = None, 
    error_message: Optional[str] = None, 
    recovery_hint: Optional[str] = None
) -> Dict[str, Any]:
    """
    Standardizes the return structure for all tools to ensure high-density feedback 
    for the ReAct agent.
    
    Args:
        status: "success", "error", or "warning"
        data: The primary result of the tool execution.
        metadata: Additional contextual information (state_delta, verification_snippets, etc.)
        error_code: Semantic error code (e.g., "FILE_NOT_FOUND")
        error_message: Human-readable error description.
        recovery_hint: Suggested next action for the agent to resolve the error.
    """
    response = {
        "status": status,
        "data": data,
        "metadata": metadata or {},
        "error": None
    }
    
    if status == "error" or error_code:
        response["error"] = {
            "code": error_code or "UNKNOWN_ERROR",
            "message": error_message or "An unexpected error occurred.",
            "recovery_hint": recovery_hint or "Review the previous action and try a different approach."
        }
        
    return response
