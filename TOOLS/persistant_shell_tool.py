# ======================================================================|
# persistent_shell_tool.py                                             |
# Production-grade persistent bash shell tool for Momobot.            |
# - True bash persistence (cd, export, source survive across calls)    |
# - Sentinel-delimited output protocol                                 |
# - Output truncation with char budget                                 |
# - Structured LLM-readable return values                              |
# - Command audit log (shell_history.jsonl)                            |
# - Lightweight dangerous-pattern guard                                |
# - Auto-restart with failure counter                                  |
# - Rich terminal UI                                                   |
# ======================================================================|

import subprocess
import sys
import os
import json
import shlex
import threading
import time
from pathlib import Path
from datetime import datetime
from langchain_core.tools import Tool
from rich.console import Console
from momo.WORKSPACE.output.momobot.bootstrap import WORKSPACE_DIR
from momo.WORKSPACE.output.momobot.bootstrap import SCRIPT_DIR
workspace = WORKSPACE_DIR
# ======================================================================|
# CONSTANTS & CONFIG                                                    |
# ======================================================================|

_console        = Console()
_BULLET         = "✽ "
_NEST    = "[dim]   └─[/dim]"

DEFAULT_TIMEOUT = 120          # seconds — agent calls that hang are worse than failing fast
MAX_OUTPUT_CHARS = 4000       # total stdout+stderr budget returned to the LLM
RESTART_LIMIT   = 3           # consecutive failures before hard error

AUDIT_LOG       = SCRIPT_DIR / "shell_history.jsonl"

# Dangerous patterns — blocked before reaching the shell
_BLOCKLIST = [
    "rm -rf /",
    "rm -rf ~",
    "dd if=",
    "mkfs",
    ":(){ :|:& };:",     # fork bomb
    "> /dev/sda",
    "chmod -R 777 /",
]

# ======================================================================|
# SHELL PROCESS STATE                                                   |
# ======================================================================|

_bash_process:  subprocess.Popen | None = None
_fail_count:    int = 0
_lock:          threading.Lock = threading.Lock()

# Unique sentinel — unlikely to appear in real output
_SENTINEL = "__MOMOBOT_SHELL_END_A3F9__"


# ======================================================================|
# AUDIT LOG                                                             |
# ======================================================================|

def _log(command: str, stdout: str, stderr: str, exit_code: int, elapsed: float) -> None:
    """Append one JSONL record to shell_history.jsonl."""
    record = {
        "ts":        datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "cmd":       command,
        "stdout":    stdout,
        "stderr":    stderr,
        "exit_code": exit_code,
        "elapsed_s": round(elapsed, 3),
    }
    try:
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # audit failure must never break the tool


# ======================================================================|
# DANGEROUS PATTERN GUARD                                               |
# ======================================================================|

def _check_blocklist(command: str) -> str | None:
    """Return an error message if the command matches a blocked pattern, else None."""
    for pattern in _BLOCKLIST:
        if pattern in command:
            return f"Blocked: command matches dangerous pattern '{pattern}'"

    # Warn on absolute paths outside workspace — soft block, not hard
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None  # malformed quoting — let the shell handle it

    for token in tokens:
        p = Path(token)
        if p.is_absolute():
            try:
                p.relative_to(workspace)
            except ValueError:
                return (
                    f"Blocked: absolute path '{token}' is outside workspace "
                    f"({workspace}). Use relative paths instead."
                )
    return None


# ======================================================================|
# TRUE PERSISTENT BASH PROCESS                                          |
# ======================================================================|

def _start_bash() -> subprocess.Popen:
    """Spawn a real /bin/bash process anchored to the workspace."""
    env = os.environ.copy()
    env["HOME"] = str(workspace)

    proc = subprocess.Popen(
        ["/bin/bash", "--norc", "--noprofile"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(workspace),
        text=True,
        bufsize=1,          # line-buffered
        env=env,
    )
    # Immediately redirect stderr into stdout inside bash so we can
    # read a single stream and still capture both.
    # We do this by sending an initial command.
    _send_raw(proc, "exec 2>&1")
    return proc


def _send_raw(proc: subprocess.Popen, cmd: str) -> None:
    """Write a command + sentinel echo to bash stdin. Does not read output."""
    proc.stdin.write(cmd + "\n")
    proc.stdin.write(f"echo '{_SENTINEL}'\n")
    proc.stdin.flush()


def _read_until_sentinel(proc: subprocess.Popen, timeout: int) -> tuple[str, bool]:
    """
    Read stdout lines until the sentinel is found or timeout fires.
    Returns (output_text, timed_out).
    """
    lines: list[str] = []
    timed_out = False

    def _reader():
        for line in proc.stdout:
            stripped = line.rstrip("\n")
            if stripped == _SENTINEL:
                return
            lines.append(stripped)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        timed_out = True

    return "\n".join(lines), timed_out


def _get_exit_code(proc: subprocess.Popen, timeout: int = 5) -> int:
    """Query $? from the running bash process."""
    proc.stdin.write("echo $?\n")
    proc.stdin.write(f"echo '{_SENTINEL}'\n")
    proc.stdin.flush()

    result, _ = _read_until_sentinel(proc, timeout)
    try:
        return int(result.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return -1


def _get_bash() -> subprocess.Popen:
    """Return the singleton bash process, restarting if dead."""
    global _bash_process
    if _bash_process is None or _bash_process.poll() is not None:
        _bash_process = _start_bash()
        # Consume the sentinel from the exec 2>&1 init command
        _read_until_sentinel(_bash_process, timeout=5)
    return _bash_process


# ======================================================================|
# CORE EXECUTION                                                        |
# ======================================================================|

def run_persistent_bash(command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """
    Execute *command* in a truly persistent /bin/bash process.

    State (cwd, env vars, activated venvs) survives across calls.
    Returns a structured string suitable for LLM reasoning.

    Args:
        command: Shell command to execute.
        timeout: Max seconds to wait for output. Default 15s.
    """
    global _bash_process, _fail_count

    # ── Hard failure guard ────────────────────────────────────────────
    if _fail_count >= RESTART_LIMIT:
        return (
            "SHELL ERROR: The bash process has failed 3 consecutive times and "
            "has been disabled. Investigate the cause before retrying shell commands."
        )

    # ── Dangerous pattern check ───────────────────────────────────────
    block_reason = _check_blocklist(command)
    if block_reason:
        _log(command, "", block_reason, -1, 0.0)
        _console.print()
        _console.print(f"{_BULLET} [bold cyan]Bash Tool[/bold cyan]  [dim red]BLOCKED[/dim red]")
        _console.print(f"{_NEST} [dim]{command}[/dim]")
        _console.print(f"{_NEST} [bold red]⚠ {block_reason}[/bold red]")
        _console.print()
        return f"EXIT CODE: -1\nBLOCKED: {block_reason}"

    # ── Execute ───────────────────────────────────────────────────────
    with _lock:
        t_start = time.monotonic()

        try:
            bash = _get_bash()
            _send_raw(bash, command)
            raw_output, timed_out = _read_until_sentinel(bash, timeout)

            if timed_out:
                bash.kill()
                _bash_process = None
                _fail_count += 1
                elapsed = time.monotonic() - t_start
                msg = f"TIMEOUT: command exceeded {timeout}s and was killed. Shell restarted."
                _log(command, "", msg, -1, elapsed)
                _render_ui(command, "", msg, -1, elapsed, timed_out=True)
                return f"EXIT CODE: -1\nTIMEOUT: {timeout}s\nThe command was killed. Shell has been restarted."

            exit_code = _get_exit_code(bash, timeout=5)
            elapsed = time.monotonic() - t_start
            _fail_count = 0  # reset on success

        except (BrokenPipeError, OSError) as exc:
            _bash_process = None
            _fail_count += 1
            elapsed = time.monotonic() - t_start
            msg = f"Shell pipe error: {exc}"
            _log(command, "", msg, -1, elapsed)
            return f"EXIT CODE: -1\nSHELL ERROR: {msg}\nShell has been restarted. Please retry."

    # ── Truncate output ───────────────────────────────────────────────
    truncated = False
    original_len = len(raw_output)
    if original_len > MAX_OUTPUT_CHARS:
        raw_output = raw_output[:MAX_OUTPUT_CHARS]
        truncated = True

    # ── Audit log ─────────────────────────────────────────────────────
    _log(command, raw_output, "", exit_code, elapsed)

    # ── Terminal UI ───────────────────────────────────────────────────
    _render_ui(command, raw_output, "", exit_code, elapsed, truncated=truncated, original_len=original_len)

    # ── Structured return for LLM ─────────────────────────────────────
    return _format_result(command, raw_output, exit_code, elapsed, truncated, original_len)


# ======================================================================|
# FORMATTING                                                            |
# ======================================================================|

def _render_ui(
    command: str,
    output: str,
    error: str,
    exit_code: int,
    elapsed: float,
    timed_out: bool = False,
    truncated: bool = False,
    original_len: int = 0,
) -> None:
    """Print Rich terminal output."""
    status = "[bold red]TIMEOUT[/bold red]" if timed_out else (
        "[green4]✔[/green4]" if exit_code == 0 else f"[bold red]✘ exit {exit_code}[/bold red]"
    )
    _console.print()
    _console.print(f"{_BULLET} [bold cyan]Bash Tool[/bold cyan]  {status}  [dim]{elapsed:.2f}s[/dim]")
    _console.print(f"{_NEST} [dim]{command}[/dim]")

    if output:
        _console.print(output.rstrip())

    if error:
        _console.print(f"{_NEST} [bold red]⚠ stderr:[/bold red] {error.rstrip()}")

    if truncated:
        omitted = original_len - MAX_OUTPUT_CHARS
        _console.print(f"{_NEST} [dim yellow]⚠ output truncated — {omitted:,} chars omitted[/dim yellow]")

    _console.print()


def _format_result(
    command: str,
    output: str,
    exit_code: int,
    elapsed: float,
    truncated: bool,
    original_len: int,
) -> str:
    """Return a structured string optimised for LLM reasoning."""
    lines = [
        f"EXIT CODE: {exit_code}",
        f"ELAPSED:   {elapsed:.2f}s",
    ]

    if output.strip():
        lines.append(f"OUTPUT:\n{output.rstrip()}")
    else:
        lines.append("OUTPUT: (none)")

    if truncated:
        omitted = original_len - MAX_OUTPUT_CHARS
        lines.append(f"[TRUNCATED: {omitted:,} chars omitted — use head/tail/grep to narrow output]")

    return "\n".join(lines)


# ======================================================================|
# UTILITY — QUERY SHELL STATE                                           |
# ======================================================================|

def get_shell_state() -> str:
    """
    Return current working directory and key env vars from the live bash process.
    Useful for the agent to orient itself without running a full command.
    """
    return run_persistent_bash(
        "echo CWD=$(pwd) && echo VENV=${VIRTUAL_ENV:-none} && echo SHELL_PID=$$",
        timeout=5,
    )


# ======================================================================|
# LANGCHAIN TOOL DEFINITION                                             |
# ======================================================================|

bash_tool = Tool(
    name="bash_shell",
    func=run_persistent_bash,
    description=(
        "Runs a shell command in a PERSISTENT /bin/bash process anchored to the workspace. "
        "State persists across calls: 'cd', 'export', 'source venv/bin/activate' all survive. "
        "Use for: filesystem operations (ls, mkdir, cat, cp, mv, rm), "
        "running scripts (python script.py, node index.js), "
        "installing packages (pip install, npm install), "
        "git operations, or any OS-level command. "
        "Output is capped at 4000 chars — use head/tail/grep for large outputs. "
        "Default timeout is 15s; long-running installs may need explicit timeout arg. "
        "Input: a single shell command string, e.g. 'ls -la' or 'pip install requests'."
    ),
)
