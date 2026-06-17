from langchain_core.tools import tool
import difflib
from pathlib import Path
from rich.console import Console
from rich.markup import escape
from setup import WORKSPACE_DIR
import re

_console = Console()
_BULLET  = "[green3]●[/green3]"
_NEST    = "[dim]  ⎿[/dim]"


@tool
def str_replace_tool(path: str, old_str: str, new_str: str) -> str:
    """Edit a specific string in a file without rewriting the whole file.
    Use this after reading a file when you want to change a specific section.
    old_str must appear EXACTLY once in the file.
    Returns a diff showing lines removed (-) and added (+).

    Args:
        path: File path relative to workspace (e.g. 'src/main.py')
        old_str: Exact text to find — must appear exactly once, whitespace and indentation must match
        new_str: Replacement text
    """
    if not path:
        return "Error: 'path' is required."
    if old_str == "":
        return "Error: 'old_str' cannot be empty."

    full_path = Path(WORKSPACE_DIR) / path

    if not full_path.exists():
        return f"Error: File not found — {path}"
    if not full_path.is_file():
        return f"Error: '{path}' is not a file."

    original = full_path.read_text(encoding="utf-8")

    count = len(re.findall(re.escape(old_str), original))
    if count == 0:
        return (
            f"Error: 'old_str' not found in {path}.\n"
            "Tip: Make sure whitespace and indentation match exactly."
        )
    if count > 1:
        return (
            f"Error: 'old_str' appears {count} times in {path}. "
            "It must be unique. Add more context to make it unambiguous."
        )

    updated = original.replace(old_str, new_str, 1)
    full_path.write_text(updated, encoding="utf-8")

    diff_lines = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    ))

    if not diff_lines:
        return "No changes made (old_str and new_str were identical)."

    _console.print(f"{_BULLET} [bold]Editing File[/bold]")
    _console.print(f"{_NEST} [dim]{path}[/dim]")

    for line in diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue
        elif line.startswith("@@"):
            _console.print(f"[dim]{escape(line)}[/dim]")
        elif line.startswith("-"):
            _console.print(f"[red]{escape(line)}[/red]")
        elif line.startswith("+"):
            _console.print(f"[green]{escape(line)}[/green]")
        else:
            _console.print(escape(line))

    _console.print()

    diff_output = "".join(diff_lines)
    return f"✓ Edit applied to `{path}`\n\n```diff\n{diff_output}\n```"