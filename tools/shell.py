#!/usr/bin/env python3
"""
shell.py — Persistent shell tool for agents, split by platform.

Linux/macOS: one persistent bash process, sentinel-based output capture.
  cwd/env persist naturally because the shell process itself stays alive.

Windows: no persistent process. Each call spawns a fresh PowerShell
  process; cwd and env-var changes are tracked in Python and replayed
  into the next call's script. This sidesteps PowerShell's stdin-script
  mode, which isn't a reliable multi-round-trip REPL the way
  `bash --norc --noprofile` is — trying to keep one PowerShell process
  alive over a trickle-fed stdin pipe is what was breaking the old
  single-persistent-process design for Windows.

Only the shells this file can actually speak to are supported (bash on
POSIX; pwsh/powershell on Windows) — no more shell_candidates list that
promised fish/cmd/etc. support the exit-code and redirect syntax never
covered.
"""

import os
import platform
import shutil
import subprocess
import threading
import time

from langchain_core.tools import tool
from tools.response_handler import create_tool_response

from bootstrap import WORKSPACE_DIR, config

workspace = WORKSPACE_DIR
IS_WINDOWS = platform.system() == "Windows"

TIMEOUT = 10       # seconds per command
MAX_OUTPUT = 4000  # characters (stdout+stderr)


# ---------------------------------------------------------------------
# Shared: build the create_tool_response payload, truncate
# ---------------------------------------------------------------------
def _finalize(command, exit_code, output, elapsed, extra_metadata=""):
    truncated = False
    orig_len = len(output)
    if orig_len > MAX_OUTPUT:
        output = output[:MAX_OUTPUT]
        truncated = True

    shell_label = "powershell" if IS_WINDOWS else "bash"

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
        metadata={"state_delta": f"Ran '{command}' ({shell_label}). {extra_metadata}".strip()}
    )


# ---------------------------------------------------------------------
# Linux / macOS — persistent bash, sentinel-based
# ---------------------------------------------------------------------
if not IS_WINDOWS:
    SHELL_NAME = config.get("shell", "bash").strip().lower()
    if SHELL_NAME not in ("bash", "zsh", "sh"):
        # Only POSIX-sh-compatible shells are actually supported by the
        # `exec 2>&1` / `echo $?` protocol below — fish ($status, not $?)
        # and anything else silently fall back rather than pretending to work.
        SHELL_NAME = "bash"

    SHELL_EXE = shutil.which(SHELL_NAME)
    if SHELL_EXE is None:
        raise RuntimeError(f"Shell '{SHELL_NAME}' not found on PATH.")

    SENTINEL = "__SHELL_END_SENTINEL__"
    _process = None
    _lock = threading.Lock()

    def _start_shell():
        env = os.environ.copy()
        env["HOME"] = str(workspace)
        proc = subprocess.Popen(
            [SHELL_EXE, "--norc", "--noprofile"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(workspace),
            text=True,
            bufsize=1,
            env=env,
        )
        proc.stdin.write("exec 2>&1\n")
        proc.stdin.write(f"echo '{SENTINEL}'\n")
        proc.stdin.flush()
        # Consume the sentinel we just emitted, or the reader thread on the
        # first real command ends up racing a leftover sentinel forever.
        _read_until_sentinel(proc, timeout=5)
        return proc

    def _get_shell():
        global _process
        if _process is None or _process.poll() is not None:
            _process = _start_shell()
        return _process

    def _send_command(proc, cmd):
        proc.stdin.write(cmd + "\n")
        proc.stdin.write("echo $?\n")
        proc.stdin.write(f"echo '{SENTINEL}'\n")
        proc.stdin.flush()

    def _read_until_sentinel(proc, timeout):
        lines = []
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
        return "\n".join(lines), t.is_alive()

    def _execute(command: str, timeout: int = TIMEOUT) -> dict:
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
                raw_lines = raw_output.split("\n") if raw_output else []
                if raw_lines:
                    exit_code_str, output_lines = raw_lines[-1], raw_lines[:-1]
                else:
                    exit_code_str, output_lines = "", []
                try:
                    exit_code = int(exit_code_str.strip())
                except ValueError:
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

            return _finalize(command, exit_code, output, elapsed,
                              "cwd/env persist inside the shell process.")


# ---------------------------------------------------------------------
# Windows — no persistent process; fresh PowerShell per call, with
# cwd/env tracked in Python and replayed into each new script.
# ---------------------------------------------------------------------
else:
    _configured = config.get("shell")
    if _configured in ("pwsh", "powershell"):
        WIN_SHELL_EXE = shutil.which(_configured)
    else:
        WIN_SHELL_EXE = shutil.which("pwsh") or shutil.which("powershell")
    if WIN_SHELL_EXE is None:
        raise RuntimeError("Neither 'pwsh' nor 'powershell' was found on PATH.")

    _CWD_MARK = "__MOMO_CWD__:"
    _EXIT_MARK = "__MOMO_EXIT__:"
    _ENV_BEGIN = "__MOMO_ENV_BEGIN__"
    _ENV_END = "__MOMO_ENV_END__"

    _win_lock = threading.Lock()
    _win_cwd = str(workspace)
    _win_env_overrides = {}   # name -> value, differs from the process baseline
    _win_removed_vars = []    # names present in baseline but deleted by the user
    # Baseline is lazily captured from the FIRST PowerShell call's own env
    # dump — not from Python's os.environ. PowerShell's own startup can
    # add/rewrite a few vars (PSModulePath and friends), so diffing against
    # a different process's environment produces false "removed" positives.
    # Comparing apples to apples (fresh-pwsh-dump vs fresh-pwsh-dump) avoids
    # that class of bug entirely.
    _win_base_env = None

    def _win_build_script(command: str) -> str:
        esc_cwd = _win_cwd.replace("'", "''")
        lines = [f"Set-Location -LiteralPath '{esc_cwd}'"]
        # Env var names go through -Path with the drive prefix built from a
        # quoted string, never as bare `Env:NAME` / `$env:NAME` tokens — names
        # like `ProgramFiles(x86)` break bareword syntax because PowerShell's
        # parser reads the trailing `(x86)` as a sub-expression (a command
        # call) rather than part of the name.
        for name in _win_removed_vars:
            esc_name = name.replace("'", "''")
            lines.append(f"Remove-Item -Path ('Env:' + '{esc_name}') -ErrorAction SilentlyContinue")
        for name, value in _win_env_overrides.items():
            esc_name = name.replace("'", "''")
            esc_val = value.replace("'", "''")
            lines.append(f"Set-Item -Path ('Env:' + '{esc_name}') -Value '{esc_val}'")
        lines.append(f"{command} *>&1")
        lines.append(
            "$__momo_code = if ($LASTEXITCODE -ne $null) { $LASTEXITCODE } "
            "else { if ($?) { 0 } else { 1 } }"
        )
        lines.append(f"Write-Output ('{_CWD_MARK}' + (Get-Location).Path)")
        lines.append(f"Write-Output ('{_EXIT_MARK}' + $__momo_code)")
        lines.append(f"Write-Output '{_ENV_BEGIN}'")
        lines.append('Get-ChildItem Env: | ForEach-Object { "$($_.Name)=$($_.Value)" }')
        lines.append(f"Write-Output '{_ENV_END}'")
        return "\n".join(lines)

    def _win_execute(command: str, timeout: int = TIMEOUT) -> dict:
        global _win_cwd, _win_env_overrides, _win_removed_vars, _win_base_env
        with _win_lock:
            start = time.monotonic()
            script = _win_build_script(command)

            try:
                proc = subprocess.run(
                    [WIN_SHELL_EXE, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return create_tool_response(
                    status="error",
                    data={"command": command, "timeout": timeout},
                    error_code="TIMEOUT",
                    error_message=f"Command timed out after {timeout}s.",
                    recovery_hint=(
                        "No process was left running — each Windows call is a fresh PowerShell "
                        "process, so cwd/env state from before this call is still intact. Retry "
                        "the command or break it into smaller steps."
                    )
                )
            elapsed = time.monotonic() - start

            raw_lines = (proc.stdout or "").splitlines()
            output_lines, env_lines = [], []
            exit_code, new_cwd, in_env = -1, _win_cwd, False

            for line in raw_lines:
                if line == _ENV_BEGIN:
                    in_env = True
                    continue
                if line == _ENV_END:
                    in_env = False
                    continue
                if in_env:
                    env_lines.append(line)
                    continue
                if line.startswith(_CWD_MARK):
                    new_cwd = line[len(_CWD_MARK):]
                    continue
                if line.startswith(_EXIT_MARK):
                    try:
                        exit_code = int(line[len(_EXIT_MARK):].strip())
                    except ValueError:
                        exit_code = -1
                    continue
                output_lines.append(line)

            if proc.stderr:
                output_lines.append(proc.stderr.rstrip())

            new_env = {}
            for line in env_lines:
                if "=" in line:
                    k, _, v = line.partition("=")
                    new_env[k.upper()] = v

            if _win_base_env is None:
                # First call: this dump *is* the baseline for "a fresh
                # PowerShell process" — not Python's own environment.
                _win_base_env = new_env
                _win_env_overrides = {}
                _win_removed_vars = []
            else:
                _win_env_overrides = {k: v for k, v in new_env.items() if _win_base_env.get(k) != v}
                _win_removed_vars = [k for k in _win_base_env if k not in new_env]
            _win_cwd = new_cwd or _win_cwd

            output = "\n".join(output_lines)
            return _finalize(command, exit_code, output, elapsed,
                              "cwd/env tracked in Python, replayed into the next call.")


# ---------------------------------------------------------------------
# LangChain tool
# ---------------------------------------------------------------------
@tool
def shell(command: str, timeout: int = TIMEOUT) -> dict:
    """Run a shell command. Persistent bash on Linux/macOS; a fresh
    PowerShell process per call on Windows, with cwd and env vars
    replayed from the previous call. cwd/env persist across calls
    either way."""
    if IS_WINDOWS:
        return _win_execute(command, timeout)
    return _execute(command, timeout)


shell.description = (
    "Run a shell command (persistent bash on Linux/macOS, per-call PowerShell on Windows). "
    f"cwd and env vars persist across calls either way. Output capped at {MAX_OUTPUT} chars, "
    f"timeout {TIMEOUT}s. Example: 'ls -la' or 'Get-ChildItem'."
)


if __name__ == "__main__":
    # Standalone test harness. Uses plain print() — this block only runs when
    # the file is executed directly (python shell.py), never via the agent.
    print("Testing a normal command...")
    print(shell.invoke({"command": "echo hello" if not IS_WINDOWS else "Write-Output hello"}))

    print("\nTesting persistence (cd) across calls...")
    if IS_WINDOWS:
        print(shell.invoke({"command": "cd C:\\Windows"}))
        print(shell.invoke({"command": "Get-Location"}))
        print("\nTesting env-var persistence...")
        print(shell.invoke({"command": "$env:MOMO_TEST = 'abc'"}))
        print(shell.invoke({"command": "echo $env:MOMO_TEST"}))
    else:
        print(shell.invoke({"command": "cd /tmp"}))
        print(shell.invoke({"command": "pwd"}))

    print("\nTesting a non-zero exit (should still be status=success, exit_code!=0)...")
    if IS_WINDOWS:
        print(shell.invoke({"command": "Select-String -Path $env:WINDIR\\win.ini -Pattern nonexistent_pattern"}))
    else:
        print(shell.invoke({"command": "grep nonexistent_pattern /etc/hostname"}))

    print("\nTesting timeout handling...")
    if IS_WINDOWS:
        print(shell.invoke({"command": "Start-Sleep -Seconds 5", "timeout": 1}))
    else:
        print(shell.invoke({"command": "sleep 5", "timeout": 1}))