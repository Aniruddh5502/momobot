import json, os, subprocess, tempfile
from typing import TypedDict, Literal, List, Optional, Dict, Any
from pathlib import Path
from langchain_core.tools import tool
from rich.console import Console
from utils.bootstrap import STATE_DIR, WORKSPACE_DIR
from tools.response_handler import create_tool_response
console = Console()
try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False

# ============================================================================
# STYLING
# ============================================================================
theme_char = "✽"

# ============================================================================
# CONFIGURATION
# ============================================================================

AUDIT_LOG_FILE = str(Path(__file__).parent / "task_state_audit.jsonl")
MAX_REPLAN_HISTORY = 20
MAX_RETRIES = 5  # For Windows file locking retries
RETRY_DELAY = 0.2  # seconds

stateFile = STATE_DIR / "state.json"
lockFile  = STATE_DIR / "state.lock"

VALID_STATUSES = {"pending", "in_progress", "done", "failed", "superseded"}
MAX_VERIFY_OUTPUT = 4000  # chars — keeps a runaway verify_cmd from blowing up agent context


class Task(TypedDict):
    id              :   str
    name            :   str
    deliverable     :   str
    verify_cmd      :   str
    depends_on      :   list[str]
    status          :   Literal["pending", "in_progress", "done", "failed", "superseded"]
    evidence        :   Optional[str]


class TaskValidationError(ValueError):
    """Raised when task input from the agent fails validation."""
    pass


def normalize_task(t: Dict[str, Any], strict: bool = False) -> Task:
    """
    Ensures a task dictionary contains all required fields.

    strict=True  (agent-provided input, e.g. task_init/task_replan):
        raises TaskValidationError on a missing id/name/verify_cmd instead of
        silently substituting placeholders — bad input becomes a clean tool
        error instead of corrupting state with duplicate "unknown" ids.
    strict=False (loading from disk):
        never raises — defensively repairs anything missing or corrupt so a
        damaged state.json can't crash the harness on startup.
    """
    tid = t.get("id")
    name = t.get("name")
    verify_cmd = t.get("verify_cmd")

    if strict:
        if not tid or not isinstance(tid, str):
            raise TaskValidationError(f"Task missing required 'id': {t!r}")
        if not name or not isinstance(name, str):
            raise TaskValidationError(f"Task '{tid}' missing required 'name'.")
        if not verify_cmd or not isinstance(verify_cmd, str):
            raise TaskValidationError(f"Task '{tid}' missing required 'verify_cmd'.")

    depends_on = t.get("depends_on", [])
    if not isinstance(depends_on, list):
        depends_on = [depends_on] if depends_on else []

    status = t.get("status", "pending")
    if status not in VALID_STATUSES:
        status = "pending"

    return {
        "id": str(tid) if tid else "unknown",
        "name": str(name) if name else "Unnamed Task",
        "deliverable": str(t.get("deliverable", "No deliverable specified")),
        "verify_cmd": str(verify_cmd) if verify_cmd else "true",
        "depends_on": [str(d) for d in depends_on],
        "status": status,
        "evidence": t.get("evidence"),
    }


def _detect_cycle(candidate_state: Dict[str, Task]) -> Optional[List[str]]:
    """DFS cycle detection over depends_on edges. Returns the cycle path if one exists."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in candidate_state}
    path: List[str] = []

    def visit(tid: str) -> Optional[List[str]]:
        color[tid] = GRAY
        path.append(tid)
        for dep in candidate_state.get(tid, {}).get("depends_on", []):
            if dep not in candidate_state:
                continue  # missing refs are handled separately
            if color.get(dep) == GRAY:
                return path[path.index(dep):] + [dep]
            if color.get(dep, WHITE) == WHITE:
                cyc = visit(dep)
                if cyc:
                    return cyc
        path.pop()
        color[tid] = BLACK
        return None

    for tid in candidate_state:
        if color[tid] == WHITE:
            cyc = visit(tid)
            if cyc:
                return cyc
    return None


def _missing_dependencies(candidate_state: Dict[str, Task]) -> Dict[str, List[str]]:
    """{task_id: [missing_dep_ids]} for any depends_on referencing an unknown task."""
    missing = {}
    for tid, t in candidate_state.items():
        gone = [d for d in t.get("depends_on", []) if d not in candidate_state]
        if gone:
            missing[tid] = gone
    return missing


class _StateLock:
    """Advisory file lock around writes to state.json, so two processes
    (e.g. a spawned subagent and its parent) can't interleave writes.
    Best-effort no-op on platforms without fcntl."""

    def __enter__(self):
        if _HAS_FCNTL:
            self._fh = open(lockFile, "w")
            fcntl.flock(self._fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        if _HAS_FCNTL:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()


def load() -> Dict[str, Task]:
    """Loads state from disk and normalizes all tasks. Falls back to the
    last good backup if state.json is corrupt, instead of silently wiping it."""
    if stateFile.exists():
        try:
            raw_data = json.loads(stateFile.read_text())
            if isinstance(raw_data, dict):
                return {tid: normalize_task(tval) for tid, tval in raw_data.items()}
            else:
                return {}
        except Exception as e:
            if __name__ == "__main__":
                console.print(f"{theme_char} [red]Error loading state: {e}[/red]")
            backup = stateFile.with_suffix(".json.bak")
            if backup.exists():
                try:
                    raw_data = json.loads(backup.read_text())
                    if __name__ == "__main__":
                        console.print(f"{theme_char} [yellow]Recovered state from backup.[/yellow]")
                    return {tid: normalize_task(tval) for tid, tval in raw_data.items()}
                except Exception:
                    return {}
            else:
                return {}
    else:
        return {}


def save(state: Dict[str, Task]):
    """Persists current state atomically: write to a temp file, fsync, then
    rename over state.json (rename is atomic on the same filesystem, so a
    crash mid-write can't leave a truncated/corrupt file). Keeps a rolling
    .bak of the previous good state for recovery."""
    with _StateLock():
        if stateFile.exists():
            try:
                stateFile.replace(stateFile.with_suffix(".json.bak"))
            except Exception:
                pass
        fd, tmp_path = tempfile.mkstemp(dir=str(STATE_DIR), prefix=".state_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(state, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, stateFile)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise


def can_start(state: Dict[str, Task], task_id: str) -> tuple[bool, str]:
    """Validates if a task is eligible to start based on status and dependencies."""
    if task_id not in state:
        return False, "Task ID not found."

    task = state[task_id]

    if task.get("status") != "pending":
        return False, f"Task is already {task.get('status')}."

    for dep_id in task.get("depends_on", []):
        dep = state.get(dep_id)
        if not dep or dep.get("status") != "done":
            return False, f"Dependency {dep_id} is not done."

    for t_id, t_val in state.items():
        if t_val.get("status") == "in_progress":
            return False, f"Task {t_id} is currently in progress."

    return True, "Ready to start."


def _run_verify(cmd: str) -> tuple[bool, str]:
    """Internal helper to run the verify shell command."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(WORKSPACE_DIR),
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        if len(output) > MAX_VERIFY_OUTPUT:
            output = output[:MAX_VERIFY_OUTPUT] + f"\\n...[truncated, {len(output)} chars total]"
        return (result.returncode == 0), output
    except subprocess.TimeoutExpired:
        return False, "Verification command timed out after 30s."
    except Exception as e:
        return False, str(e)


@tool
def task_init(tasks: List[Dict[str, Any]]) -> dict:
    """
    Initializes the project plan. Replaces any existing plan.
    Args:
        tasks: List of task objects. Required per task: id, name, verify_cmd.
               Optional: deliverable, depends_on.
    """
    if not tasks:
        return create_tool_response(status="error", error_code="EMPTY_PLAN", error_message="tasks list is empty.")

    try:
        new_state: Dict[str, Task] = {}
        for t in tasks:
            norm_t = normalize_task(t, strict=True)
            if norm_t["id"] in new_state:
                raise TaskValidationError(f"Duplicate task id in plan: '{norm_t['id']}'")
            norm_t["status"] = "pending"
            new_state[norm_t["id"]] = norm_t
    except TaskValidationError as e:
        return create_tool_response(status="error", error_code="INVALID_TASK", error_message=str(e))

    missing = _missing_dependencies(new_state)
    if missing:
        return create_tool_response(
            status="error", error_code="MISSING_DEPENDENCY",
            error_message=f"Tasks reference unknown dependencies: {missing}"
        )

    cycle = _detect_cycle(new_state)
    if cycle:
        return create_tool_response(
            status="error", error_code="DEPENDENCY_CYCLE",
            error_message=f"Dependency cycle detected: {' -> '.join(cycle)}"
        )

    try:
        save(new_state)
    except Exception as e:
        console.print(f"{theme_char} [dim red]Plan initialization failed: {e}[/dim red]")
        return create_tool_response(status="error", error_code="SAVE_FAILED", error_message=str(e))

    
    console.print(f"{theme_char} [dim]Project plan initialized with {len(new_state)} tasks.[/dim]")
    
    return create_tool_response(
        status="success",
        data={"tasks_initialized": list(new_state.keys())},
        metadata={"state_delta": "Plan initialized"}
    )


@tool
def task_update(id: str, action: Literal["start", "submit"], evidence: Optional[str] = None) -> dict:
    """
    Updates the state of a task.
    - 'start': Moves pending -> in_progress.
    - 'submit': Runs verify_cmd. Success -> done, Fail -> failed. Optional
      `evidence` (e.g. a summary of what was done) is stored on the task.
    """
    state = load()  # Ensure we have freshest state

    if id not in state:
        return create_tool_response(status="error", error_code="TASK_NOT_FOUND", error_message=f"Task {id} not found.")

    if action not in ("start", "submit"):
        return create_tool_response(status="error", error_code="INVALID_ACTION", error_message=f"Unknown action '{action}'.")

    try:
        if action == "start":
            allowed, reason = can_start(state, id)
            if not allowed:
                console.print(f"{theme_char} [dim red]Task start failed: {reason}[/dim red]")
                return create_tool_response(status="error", error_code="PRECONDITION_FAILED", error_message=reason)

            state[id]["status"] = "in_progress"
            save(state)
            console.print(f"{theme_char} [dim]Task {id} started successfully[/dim]")
            return create_tool_response(
                status="success",
                data={"id": id, "status": "in_progress"},
                metadata={"state_delta": f"Task {id} started"}
            )

        # action == "submit"
        if state[id].get("status") != "in_progress":
            return create_tool_response(status="error", error_code="INVALID_STATE", error_message="Task must be in_progress to submit.")

        verify_cmd = state[id].get("verify_cmd", "true")
        success, output = _run_verify(verify_cmd)

        if evidence:
            state[id]["evidence"] = evidence

        if success:
            state[id]["status"] = "done"
            save(state)
            console.print(f"{theme_char}    [dim]Verification by harness succesfull. Marking task as done[/dim] [green]ID: {id}[/green]")
            return create_tool_response(
                status="success",
                data={"id": id, "status": "done", "verification": "Passed"},
                metadata={"state_delta": f"Task {id} verified and completed"}
            )
        else:
            state[id]["status"] = "failed"
            save(state)
            console.print(f"{theme_char} [red]Verification failed for task {id}[/red]")
            return create_tool_response(
                status="error",
                data={"id": id, "output": output},
                error_code="VERIFICATION_FAILED",
                error_message=f"Verification command failed: {verify_cmd}",
                recovery_hint=f"Review the output and call task_replan with this task_id. Output: {output}"
            )
    except Exception as e:
        console.print(f"{theme_char} [dim red]Task update failed: {e}[/dim red]")
        return create_tool_response(status="error", error_code="INTERNAL_ERROR", error_message=str(e))


@tool
def task_replan(failed_task_id: str, reason: str, new_tasks: List[Dict[str, Any]]) -> dict:
    """
    Retires a failed task and inserts replacement tasks.
    """
    state = load()

    if failed_task_id not in state or state[failed_task_id].get("status") != "failed":
        console.print(f"{theme_char} [dim red]Replan failed[/dim red]"); return create_tool_response(status="error", 
                                    error_code="INVALID_TASK_STATE", 
                                    error_message="Task must be 'failed' to replan.")

    if not new_tasks:
        console.print(f"{theme_char} [dim red]Replan failed[/dim red]"); return create_tool_response(status="error", 
                                    error_code="EMPTY_REPLAN", 
                                    error_message="new_tasks is empty.")

    try:
        candidate = dict(state)
        candidate[failed_task_id] = {**candidate[failed_task_id], "status": "superseded"}

        added_ids = []
        for t in new_tasks:
            norm_t = normalize_task(t, strict=True)
            existing = state.get(norm_t["id"])
            if existing and existing.get("status") not in ("failed", "superseded"):
                raise TaskValidationError(f"Replacement task id '{norm_t['id']}' collides with an existing active task.")
            norm_t["status"] = "pending"
            candidate[norm_t["id"]] = norm_t
            added_ids.append(norm_t["id"])
    except TaskValidationError as e:
        console.print(f"{theme_char} [dim red]Replan failed[/dim red]"); return create_tool_response(status="error", 
                                    error_code="INVALID_TASK", 
                                    error_message=str(e))

    missing = _missing_dependencies(candidate)
    if missing:
        console.print(f"{theme_char} [dim red]Replan failed[/dim red]"); return create_tool_response(status="error", 
                                    error_code="MISSING_DEPENDENCY", 
                                    error_message=f"Tasks reference unknown dependencies: {missing}")

    cycle = _detect_cycle(candidate)
    if cycle:
        console.print(f"{theme_char} [dim red]Replan failed[/dim red]"); return create_tool_response(status="error", 
                                    error_code="DEPENDENCY_CYCLE", 
                                    error_message=f"Dependency cycle detected: {' -> '.join(cycle)}")

    for aid in added_ids:
        if failed_task_id in candidate[aid].get("depends_on", []):
            return create_tool_response(
                status="error", 
                error_code="INVALID_DEPENDENCY",
                error_message=f"New task '{aid}' depends on superseded task '{failed_task_id}', which can never become 'done'.")

    try:
        save(candidate)
    except Exception as e:
        console.print(f"{theme_char} [dim red]Replan failed[/dim red]"); return create_tool_response(status="error", error_code="SAVE_FAILED", error_message=str(e))

    log_entry = f"Replan: Task {failed_task_id} failed. Reason: {reason}. Added {len(new_tasks)} new tasks: {added_ids}.\\n"
    try:
        with open(STATE_DIR / "progress.log", "a") as f:
            f.write(log_entry)
    except Exception:
        pass  # a logging failure shouldn't fail the whole replan

    console.print(f"{theme_char} [dim]Task replanned successfully[/dim]"); return create_tool_response(
        status="success",
        data={"superseded": failed_task_id, "added": added_ids},
        metadata={"state_delta": "Plan updated via replan"}
    )


@tool
def task_clear() -> dict:
    """Resets the entire task state."""
    try:
        if stateFile.exists():
            stateFile.unlink()
        backup = stateFile.with_suffix(".json.bak")
        if backup.exists():
            backup.unlink()
    except Exception as e:
        console.print(f"{theme_char} [dim red]Task state clear failed: {e}[/dim red]")
        return create_tool_response(status="error", error_code="CLEAR_ERROR", error_message=str(e))

    console.print(f"{theme_char} [dim]Task state cleared successfully.[/dim]")
    return create_tool_response(
        status="success",
        data={"state_cleared": True},
        metadata={"state_delta": "Full state reset"}
    )

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

class SessionManager:
    """
    Handles persisting the conversation history to disk so a user can
    resume a chat later. 
    """
    def __init__(self):
        # Use a dedicated sessions folder in the root project directory
        # instead of nesting it inside the states folder.
        from utils.bootstrap import root
        self.sessions_dir = root / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session_id: str, messages: List[Any]):
        path = self.sessions_dir / f"{session_id}.json"
        # Since messages are LangChain objects, we use a simple serialization
        serialized = []
        for m in messages:
            serialized.append({"type": type(m).__name__, "content": m.content})
        
        with open(path, "w") as f:
            json.dump(serialized, f, indent=4)

    def load_session(self, session_id: str) -> List[Any]:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return []
        
        with open(path, "r") as f:
            data = json.load(f)
        
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        mapping = {"HumanMessage": HumanMessage, "AIMessage": AIMessage, "SystemMessage": SystemMessage}
        
        if isinstance(data, dict) and "messages" in data:
            messages_list = data["messages"]
        elif isinstance(data, list):
            messages_list = data
        else:
            return []
        
        return [mapping.get(item["type"], HumanMessage)(content=item["content"]) for item in messages_list if isinstance(item, dict)]

    def list_sessions(self) -> List[str]:
        return [f.stem for f in self.sessions_dir.glob("*.json")]

    def delete_session(self, session_id: str):
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
