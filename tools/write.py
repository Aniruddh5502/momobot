import sys, json, yaml, csv, io
from pathlib                        import Path
from typing                         import Dict, Callable
from langchain_core.tools           import tool
from bootstrap                      import WORKSPACE_DIR
from tools.response_handler         import create_tool_response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

workspace = WORKSPACE_DIR


# --- Validation Handlers ---
def validate_text(content: str) -> bool:
    return True

def validate_json(content: str) -> bool:
    try:
        json.loads(content)
        return True
    except Exception:
        return False

def validate_yaml(content: str) -> bool:
    try:
        yaml.safe_load(content)
        return True
    except Exception:
        return False

def validate_csv(content: str) -> bool:
    try:
        f = io.StringIO(content)
        reader = csv.reader(f)
        for row in reader:
            pass
        return True
    except Exception:
        return False

# Handler Registry: Extension -> (Validation Function, Error Message)
WRITE_HANDLERS: Dict[str, tuple[Callable[[str], bool], str]] = {
    ".txt": (validate_text, "Invalid plain text format"),
    ".py": (validate_text, "Invalid Python code format"),
    ".js": (validate_text, "Invalid JavaScript code format"),
    ".ts": (validate_text, "Invalid TypeScript code format"),
    ".json": (validate_json, "Invalid JSON format. Please ensure the content is a valid JSON string."),
    ".yaml": (validate_yaml, "Invalid YAML format. Please ensure the content is a valid YAML string."),
    ".yml": (validate_yaml, "Invalid YAML format. Please ensure the content is a valid YAML string."),
    ".md": (validate_text, "Invalid Markdown format"),
    ".html": (validate_text, "Invalid HTML format"),
    ".css": (validate_text, "Invalid CSS format"),
    ".csv": (validate_csv, "Invalid CSV format"),
    ".env": (validate_text, "Invalid .env format"),
}

@tool
def write(filePath: str, content) -> dict:
    """
    Writes content to a file within the workspace. Creates parent directories if needed.
    Supports validation for common file types (.json, .yaml, .csv, etc.) to ensure data integrity.
    Returns a verification snippet of the written content.
    Args:
        filePath: Path relative to workspace root (e.g. 'src/main.py')
        content: Content to write to the file
    """
    
    if content is None:
        content = ""
    elif isinstance(content, (dict, list)):
        try:
            content = json.dumps(content, indent=2, ensure_ascii=False)
        except Exception as e:
            content=str(content)
    elif not isinstance(content, str):
        content = str(content)
        
    try:
        # 1. Path Validation
        target_path = (Path(workspace) / filePath).resolve()
        workspace_resolved = Path(workspace).resolve()

        try:
            target_path.relative_to(workspace_resolved)
        except ValueError:
            return create_tool_response(
                status="error",
                error_code="OUT_OF_WORKSPACE",
                error_message=f"The path '{filePath}' is outside the allowed workspace boundary.",
                recovery_hint="Ensure the path is relative to the workspace root."
            )

        # 2. File Type Validation
        ext = target_path.suffix.lower()
        if ext in WRITE_HANDLERS:
            validate_fn, error_msg = WRITE_HANDLERS[ext]
            if not validate_fn(content):
                return create_tool_response(
                    status="error",
                    error_code="INVALID_FILE_FORMAT",
                    error_message=f"Format validation failed for {ext}: {error_msg}",
                    recovery_hint=f"Ensure the content provided is a valid {ext[1:]} formatted string."
                )

        # 3. Writing Process
        is_new = not target_path.exists()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 4. Verification Snippet
        snippet = content[-50:] if len(content) > 50 else content

        return create_tool_response(
            status="success",
            data={"filePath": filePath, "bytes_written": len(content)},
            metadata={
                "state_delta": f"{'Created' if is_new else 'Updated'} {filePath} ({len(content):,} bytes)",
                "verification_snippet": f"...{snippet}",
                "full_path": str(target_path)
            }
        )

    except PermissionError:
        return create_tool_response(
            status="error",
            error_code="PERMISSION_DENIED",
            error_message=f"Insufficient permissions to write to '{filePath}'.",
            recovery_hint="Check if the file is read-only or locked."
        )
    except Exception as e:
        return create_tool_response(
            status="error",
            error_code="INTERNAL_WRITE_ERROR",
            error_message=str(e),
            recovery_hint="Check disk space or filesystem integrity."
        )
