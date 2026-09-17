#!/usr/bin/env python3
"""
simplified_shell_tool.py — Minimal persistent shell for agents.

- True persistence: cd, export, source survive across calls.
- Sentinel-based output capture.
- Timeout and truncation to keep LLM responses manageable.
- Returns structured dicts via create_tool_response (same shape as the
  read/write/task-state tools), not raw strings.
- LangChain @tool wrapper included.
"""

import subprocess
import os
import shutil
import threading
import time
from langchain_core.tools import tool
from rich.console import Console
from TOOLS.response_handler import create_tool_response

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
        proc.stdin.write(f"echo '{SENTINEL}'\n")
        proc.stdin.flush()
        # Consume the sentinel we just emitted. Without this, the reader
        # thread below blocks forever waiting for a sentinel that never
        # arrives, and lingers in the background racing with every future
        # read — which is what causes real command output to intermittently
        # go missing.
        _read_until_sentinel(proc, timeout=5)
    return proc

def _get_shell():
    """Return the running shell process, restart if dead."""
    global _process
    if _process is None or _process.poll() is not None:
        _process = _start_shell()
    return _process

def _send_command(proc, cmd):
    """
    Write command + an inline exit-code probe + sentinel, all in one
    round trip. The probe is appended immediately after `cmd` (before the
    sentinel), so the exit code we later parse is guaranteed to belong to
    `cmd` itself — not to some other statement that happened to run in
    between.
    """
    if IS_POWERSHELL and cmd != "exec 2>&1":
        cmd = f"{cmd} *>&1"   # merge stderr into stdout
        proc.stdin.write(cmd + "\n")
        proc.stdin.write(
            "if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } "
            "else { if ($?) { 0 } else { 1 } }\n"
        )
    else:
        proc.stdin.write(cmd + "\n")
        proc.stdin.write("echo $?\n")
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

# ---- Core executor ----
def _execute(command: str, timeout: int = TIMEOUT) -> dict:
    """
    Execute a command in the persistent shell and return a
    create_tool_response-shaped dict.

    status="error" is reserved for the *tool* failing to run the command
    (timeout, shell crash) — a command that runs but exits non-zero is still
    a tool-level "success"; the exit code is handed back in `data` for the
    agent to interpret (grep exiting 1 for "no match" isn't a tool error).
    """
    global _process
    with _lock:
        proc = _get_shell()
        start = time.monotonic()

        try:
            _send_command(proc, command)
            raw_output, timed_out = _read_until_sentinel(proc, timeout)

            if timed_out:
                proc.kill()
                _process = None
                return create_tool_response(
                    status="error",
                    data={"command": command, "timeout": timeout},
                    error_code="TIMEOUT",
                    error_message=f"Command timed out after {timeout}s.",
                    recovery_hint=(
                        "The persistent shell was restarted, so cwd/env changes since the "
                        "last successful command were lost. Retry the command, break it into "
                        "smaller steps, or pass a longer timeout if it's expected to run this long."
                    )
                )

            elapsed = time.monotonic() - start

            # The last line before the sentinel is always the exit-code
            # probe appended in _send_command; everything before it is the
            # command's own stdout/stderr.
            raw_lines = raw_output.split("\n") if raw_output else []
            if raw_lines:
                exit_code_str, output_lines = raw_lines[-1], raw_lines[:-1]
            else:
                exit_code_str, output_lines = "", []

            try:
                exit_code = int(exit_code_str.strip())
            except ValueError:
                # Probe line wasn't parseable (unexpected) — don't silently
                # drop it, fold it back into the output and flag the code
                # as unknown rather than guessing.
                output_lines = raw_lines
                exit_code = -1

            output = "\n".join(output_lines)

        except (BrokenPipeError, OSError) as e:
            _process = None
            return create_tool_response(
                status="error",
                data={"command": command},
                error_code="SHELL_CRASHED",
                error_message=str(e),
                recovery_hint=(
                    "The shell process crashed and has been restarted, so cwd/env changes "
                    "since the last successful command were lost. Retry the command."
                )
            )

        # Truncate
        truncated = False
        orig_len = len(output)
        if orig_len > MAX_OUTPUT:
            output = output[:MAX_OUTPUT]
            truncated = True

        # Human-readable console echo (unchanged from before)
        display = f"EXIT CODE: {exit_code}\nELAPSED: {elapsed:.2f}s\n"
        display += f"OUTPUT:\n{output.rstrip()}\n" if output.strip() else "OUTPUT: (none)\n"
        if truncated:
            display += f"[TRUNCATED: {orig_len - MAX_OUTPUT:,} chars omitted]\n"
        _console.print(f"{_BULLET} [bold cyan]{SHELL_NAME} $/>[/bold cyan]", f"[bold] {command}[/bold]")
        _console.print(f"{_NEST} Output: \n[dim]{display}[/dim]")

        return create_tool_response(
            status="success",
            data={
                "command": command,
                "exit_code": exit_code,
                "output": output,
                "elapsed_seconds": round(elapsed, 2),
                "truncated": truncated,
                "truncated_chars": (orig_len - MAX_OUTPUT) if truncated else 0,
            },
            metadata={"state_delta": f"Ran '{command}' in the persistent shell (cwd/env may have changed)."}
        )


# ---- LangChain tool ----
@tool
def shell(command: str, timeout: int = TIMEOUT) -> dict:
    """Run a shell command in a persistent shell. cwd, environment variables, and virtualenv activation persist across calls."""
    return _execute(command, timeout)

# Dynamic description (mirrors the shell name/limits actually configured),
# same as the old Tool(...) wrapper's description string.
shell.description = (
    f"Run a shell command in a persistent {SHELL_NAME} shell. "
    "State (cwd, environment, virtualenv) persists across calls. "
    f"Output is capped at {MAX_OUTPUT} characters. Timeout: {TIMEOUT}s. "
    "Example: 'ls -la' or 'pip install requests'."
)


if __name__ == "__main__":
    print("Testing a normal command...")
    print(shell.invoke({"command": "echo hello && pwd"}))

    print("\nTesting persistence (cd) across calls...")
    print(shell.invoke({"command": "cd /tmp"}))
    print(shell.invoke({"command": "pwd"}))

    print("\nTesting a non-zero exit (should still be status=success, exit_code=1)...")
    print(shell.invoke({"command": "grep nonexistent_pattern /etc/hostname"}))

    print("\nTesting timeout handling...")
    print(shell.invoke({"command": "sleep 5", "timeout": 1}))