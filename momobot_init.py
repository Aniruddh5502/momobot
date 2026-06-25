"""
momobot-init: One-time setup wizard for Momobot.
Detects shell, selects model, sets workspace, creates venv, writes config.
"""

import sys
import os
import json
import shutil
import subprocess
import venv
from pathlib import Path

# ── Re-exec guard: if not running from system python, skip (init uses system python intentionally) ──
CONFIG_DIR = Path.home() / ".momobot"
CONFIG_FILE = CONFIG_DIR / "config.json"
VENV_DIR = CONFIG_DIR / "momobot-env"


# ── Rich / prompt_toolkit may not be installed yet at init time, so we use plain terminal UI ──

def print_header():
    print("\n" + "═" * 50)
    print("         MOMOBOT — First Time Setup")
    print("═" * 50 + "\n")


def print_step(n, total, text):
    print(f"\n[{n}/{total}] {text}")
    print("─" * 40)


def prompt(text, default=None):
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"{text}{suffix}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)
    return val if val else default


def confirm(text, default="y"):
    suffix = "[Y/n]" if default == "y" else "[y/N]"
    try:
        val = input(f"{text} {suffix}: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)
    if not val:
        return default == "y"
    return val in ("y", "yes")


# ── Step 1: Check Ollama ──────────────────────────────────────────────────────

def check_ollama():
    print_step(1, 5, "Checking Ollama")
    if not shutil.which("ollama"):
        print("  ✗ Ollama not found in PATH.")
        print("  Install it from: https://ollama.com/download")
        print("  Then re-run: momobot-init\n")
        sys.exit(1)

    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if result.returncode != 0:
        print("  ✗ Ollama is installed but not running.")
        print("  Start it with: ollama serve")
        sys.exit(1)

    print("  ✓ Ollama is running.")
    return result.stdout


# ── Step 2: Model selection ───────────────────────────────────────────────────

def select_model(ollama_output):
    print_step(2, 5, "Model Selection")

    lines = ollama_output.strip().split("\n")
    models = []
    for line in lines[1:]:  # skip header row
        parts = line.split()
        if parts:
            models.append(parts[0])  # NAME column

    if not models:
        print("  No models pulled yet.")
        print("  Pull a model first, e.g.: ollama pull gemma4:27b")
        sys.exit(1)

    print("  Available models:\n")
    for i, m in enumerate(models, 1):
        print(f"    {i}. {m}")

    print()
    while True:
        raw = prompt("  Select model number", default="1")
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                print(f"  ✓ Selected: {selected}")
                return selected
            else:
                print(f"  Enter a number between 1 and {len(models)}.")
        except ValueError:
            print("  Enter a valid number.")


# ── Step 3: Workspace folder ──────────────────────────────────────────────────

def select_workspace():
    print_step(3, 5, "Workspace Folder")
    default = str(Path.home() / "momobot_workspace")
    print("  This is where Momobot stores outputs and task artifacts.")
    path_str = prompt("  Workspace path", default=default)
    workspace = Path(path_str).expanduser().resolve()

    if not workspace.exists():
        if confirm(f"  '{workspace}' doesn't exist. Create it?"):
            workspace.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {workspace}")
        else:
            print("  Aborted.")
            sys.exit(0)
    else:
        print(f"  ✓ Using: {workspace}")

    return str(workspace)


# ── Step 4: Shell detection ───────────────────────────────────────────────────

def detect_shell():
    print_step(4, 5, "Shell Detection")

    candidates = ["bash", "zsh", "fish", "pwsh", "powershell", "sh"]
    detected = []
    for shell in candidates:
        if shutil.which(shell):
            detected.append(shell)

    if not detected:
        print("  ✗ No supported shell found. Defaulting to 'sh'.")
        return "sh"

    # prefer bash > zsh > fish > pwsh > powershell > sh
    preferred_order = ["bash", "zsh", "fish", "pwsh", "powershell", "sh"]
    for shell in preferred_order:
        if shell in detected:
            print(f"  ✓ Detected shell: {shell}")
            print(f"  Available: {', '.join(detected)}")
            if len(detected) > 1:
                override = confirm(f"  Use '{shell}'?", default="y")
                if not override:
                    print("\n  Available shells:")
                    for i, s in enumerate(detected, 1):
                        print(f"    {i}. {s}")
                    while True:
                        raw = prompt("  Select shell number", default="1")
                        try:
                            idx = int(raw) - 1
                            if 0 <= idx < len(detected):
                                shell = detected[idx]
                                break
                            else:
                                print(f"  Enter a number between 1 and {len(detected)}.")
                        except ValueError:
                            print("  Enter a valid number.")
            return shell

    return "sh"


# ── Step 5: Venv creation ─────────────────────────────────────────────────────

def setup_venv(repo_root):
    print_step(5, 5, "Virtual Environment")

    venv_path = VENV_DIR
    requirements = repo_root / "requirements.txt"

    if not requirements.exists():
        print(f"  ✗ requirements.txt not found at {requirements}")
        print("  Skipping venv setup.")
        return str(venv_path)

    if venv_path.exists():
        if not confirm(f"  Venv already exists at {venv_path}. Recreate?", default="n"):
            print("  ✓ Using existing venv.")
            return str(venv_path)
        shutil.rmtree(venv_path)

    print(f"  Creating venv at {venv_path} ...")
    venv.create(str(venv_path), with_pip=True)

    # resolve pip path
    if sys.platform == "win32":
        pip = venv_path / "Scripts" / "pip.exe"
    else:
        pip = venv_path / "bin" / "pip"

    print("  Installing requirements.txt ...")
    result = subprocess.run(
        [str(pip), "install", "-r", str(requirements)],
        capture_output=False,  # show output live
    )
    if result.returncode != 0:
        print("\n  ✗ Installation failed. Check the output above.")
        sys.exit(1)

    print(f"\n  ✓ Venv ready at {venv_path}")
    return str(venv_path)


# ── Write config ──────────────────────────────────────────────────────────────

def write_config(model, workspace, shell, venv_path, repo_root):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = {
        "model": model,
        "workspace": workspace,
        "shell": shell,
        "venv": venv_path,
        "repo_root": str(repo_root),
    }
    CONFIG_FILE.write_text(json.dumps(config, indent=2))
    print(f"\n  ✓ Config written to {CONFIG_FILE}")
    return config


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(config):
    print("\n" + "═" * 50)
    print("           Setup Complete!")
    print("═" * 50)
    print(f"  Model     : {config['model']}")
    print(f"  Workspace : {config['workspace']}")
    print(f"  Shell     : {config['shell']}")
    print(f"  Venv      : {config['venv']}")
    print(f"  Config    : {CONFIG_FILE}")
    print("\n  Run Momobot with:\n")
    print("    momobot\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print_header()

    # resolve repo root as the directory containing this file
    repo_root = Path(__file__).resolve().parent

    ollama_output = check_ollama()
    model = select_model(ollama_output)
    workspace = select_workspace()
    shell = detect_shell()
    venv_path = setup_venv(repo_root)
    config = write_config(model, workspace, shell, venv_path, repo_root)
    print_summary(config)


if __name__ == "__main__":
    main()