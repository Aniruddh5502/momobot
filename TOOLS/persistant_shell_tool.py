#!/usr/bin/env python3
"""
simplified_shell_tool.py — Minimal persistent shell for agents.

- True persistence: cd, export, source survive across calls.
- Sentinel-based output capture.
- Timeout and truncation to keep LLM responses manageable.
- No audit log, no Rich UI, no blocklist, no state query.
- LangChain Tool wrapper included.
"""

import sys
import subprocess
import os
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime
from langchain_core.tools import Tool
from rich.console import Console

_console = Console()
_CORAL   = "#FF5F00"
# _BULLET  = f"[{_CORAL}]⬤[/{_CORAL}]"
_BULLET      =   "✻ "
_NEST    = "[dim]   └─[/dim]"


# ---- Environment setup (keep minimal) ----
# Assume bootstrap provides WORKSPACE_DIR, SCRIPT_DIR, config.
# If not, you can hardcode or pass them explicitly.
from bootstrap import WORKSPACE_DIR, SCRIPT_DIR, config

workspace = WORKSPACE_DIR
SHELL_NAME = config.get("shell", "bash").strip().lower()

# Resolve shell executable
shell_candidates = {
    "bash": ["bash"],
    "zsh": ["zsh"],
    "fish": ["fish"],
    "sh": ["sh"],
    "pwsh": ["pwsh"],
    "powershell": ["powershell", "powershell.exe"],
}
SHELL_EXE = None
for name in shell_candidates.get(SHELL_NAME, [SHELL_NAME]):
    found = shutil.which(name)
    if found:
        SHELL_EXE = found
        break
if SHELL_EXE is None:
    raise RuntimeError(f"Shell '{SHELL_NAME}' not found on PATH.")

IS_POWERSHELL = SHELL_NAME in ("pwsh", "powershell")

# ---- Constants ----
TIMEOUT = 10          # seconds per command
MAX_OUTPUT = 4000     # characters (stdout+stderr)
SENTINEL = "__SHELL_END_SENTINEL__"

# ---- Global process ----
_process = None
_lock = threading.Lock()

# ---- Process management ----
def _start_shell():
    """Start the persistent shell process."""
    env = os.environ.copy()
    env["HOME"] = str(workspace)

    if IS_POWERSHELL:
        args = [SHELL_EXE, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"]
    else:
        args = [SHELL_EXE, "--norc", "--noprofile"]

    proc = subprocess.Popen(
        args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(workspace),
        text=True,
        bufsize=1,
        env=env,
    )
    # For bash, merge stderr into stdout globally
    if not IS_POWERSHELL:
        proc.stdin.write("exec 2>&1\n")
        proc.stdin.flush()
        # Consume any initial output (the sentinel from the exec command)
        _read_until_sentinel(proc, timeout=5)
    return proc

def _get_shell():
    """Return the running shell process, restart if dead."""
    global _process
    if _process is None or _process.poll() is not None:
        _process = _start_shell()
    return _process

def _send_command(proc, cmd):
    """Write command + sentinel to stdin."""
    if IS_POWERSHELL and cmd != "exec 2>&1":
        cmd = f"{cmd} *>&1"   # merge stderr into stdout
    proc.stdin.write(cmd + "\n")
    proc.stdin.write(f"echo '{SENTINEL}'\n")
    proc.stdin.flush()

def _read_until_sentinel(proc, timeout):
    """Read stdout until sentinel appears, with timeout."""
    lines = []
    timed_out = False
    def reader():
        try:
            for line in proc.stdout:
                if SENTINEL in line:
                    parts = line.split(SENTINEL, 1)
                    if parts[0]:
                        lines.append(parts[0])
                    break
                lines.append(line.rstrip("\n"))
        except Exception:
            pass
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        timed_out = True
    return "\n".join(lines), timed_out

def _get_exit_code(proc):
    """Query the last exit code from the shell."""
    if IS_POWERSHELL:
        proc.stdin.write("if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } else { if ($?) { 0 } else { 1 } }\n")
    else:
        proc.stdin.write("echo $?\n")
    proc.stdin.write(f"echo '{SENTINEL}'\n")
    proc.stdin.flush()
    out, _ = _read_until_sentinel(proc, timeout=5)
    try:
        return int(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return -1

# ---- Core executor ----
def run_shell_command(command: str, timeout: int = TIMEOUT) -> str:
    """
    Execute a command in the persistent shell and return output + exit code.

    Returns:
        A simple string with exit code, elapsed time, and output (truncated).
    """
    with _lock:
        proc = _get_shell()
        start = time.monotonic()

        try:
            _send_command(proc, command)
            output, timed_out = _read_until_sentinel(proc, timeout)

            if timed_out:
                proc.kill()
                _process = None
                return f"TIMEOUT after {timeout}s – shell restarted. Command: {command}"

            exit_code = _get_exit_code(proc)
            elapsed = time.monotonic() - start

        except (BrokenPipeError, OSError) as e:
            _process = None
            return f"SHELL ERROR: {e} – shell restarted. Command: {command}"

        # Truncate
        truncated = False
        orig_len = len(output)
        if orig_len > MAX_OUTPUT:
            output = output[:MAX_OUTPUT]
            truncated = True

        # Build result string
        result = f"EXIT CODE: {exit_code}\nELAPSED: {elapsed:.2f}s\n"
        if output.strip():
            result += f"OUTPUT:\n{output.rstrip()}\n"
        else:
            result += "OUTPUT: (none)\n"
        if truncated:
            result += f"[TRUNCATED: {orig_len - MAX_OUTPUT:,} chars omitted]\n"
        
        _console.print(f"{_BULLET} [bold cyan]Bash $/>[/bold cyan]",f"[bold] {command}[/bold]")
        _console.print(f"{_NEST} Output: \n[dim]{result}[/dim]")
        return result

# ---- LangChain tool ----
bash_tool = Tool(
    name="persistent_shell",
    func=run_shell_command,
    description=(
        f"Run a shell command in a persistent {SHELL_NAME} shell. "
        "State (cwd, environment, virtualenv) persists across calls. "
        f"Output is capped at {MAX_OUTPUT} characters. Timeout: {TIMEOUT}s. "
        "Example: 'ls -la' or 'pip install requests'."
    ),
)