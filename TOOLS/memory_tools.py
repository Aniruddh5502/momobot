from langchain_core.tools import tool
import os
import time
import re
from rich.console import Console
from momo.WORKSPACE.output.momobot.bootstrap import MEMORY_DIR

_console = Console()
_BULLET  = "✻ "
_NEST    = "[dim]   └─[/dim]"


MAP_FILE = MEMORY_DIR / "MEMORY.md"
if not MAP_FILE.exists():
    MAP_FILE.write_text("`<memory_of_user>` \n\n`</memory_of_user>`")

# ============================================================================
# HELPERS
# ============================================================================

def _read_file() -> str:
    if not MAP_FILE.exists():
        return ""
    return MAP_FILE.read_text(encoding='utf-8')


def _write_file(content: str):
    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAP_FILE.write_text(content, encoding='utf-8')


def _parse_blocks(content: str) -> dict:
    """Parse MEMORY.md into {keyword: full_block_text} dict."""
    blocks = {}
    pattern = re.compile(r'^## (.+)$', re.MULTILINE)
    matches = list(pattern.finditer(content))
    for i, match in enumerate(matches):
        keyword = match.group(1).strip()
        start   = match.start()
        end     = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        blocks[keyword] = content[start:end]
    return blocks


def _build_block(keyword: str, note: str, timestamp: int) -> str:
    return f"## {keyword}\ntimestamp: {timestamp}\n{note.strip()}\n\n---\n\n"


# ============================================================================
# TOOLS
# ============================================================================

@tool
def save_memory(keyword: str, note: str) -> str:
    """
    Save a new memory block to long-term storage.
    Fails if keyword already exists — use modify_memory to update.
    Args:
        keyword: short unique label for this memory
        note: content to store
    """
    try:
        keyword = keyword.strip()
        note    = note.strip()

        if not keyword or not note:
            return "Error: keyword and note must not be empty."

        content = _read_file()
        blocks  = _parse_blocks(content)

        if keyword in blocks:
            return f"Error: '{keyword}' already exists. Use modify_memory to update it."

        new_block = _build_block(keyword, note, int(time.time()))
        _write_file(content + new_block)

        _console.print(f"{_BULLET} [bold cyan]Memory Saved[/bold cyan]")
        _console.print(f"{_NEST} [dim]{keyword}[/dim]")
        return f"✓ Memory saved: '{keyword}'"

    except Exception as e:
        return f"Error saving memory: {e}"


@tool
def recall_memory() -> str:
    """
    Read the full memory store. No input needed.
    Always call this before modify_memory so you have current content.
    """
    try:
        content = _read_file()
        if not content.strip():
            return "Memory is empty."

        _console.print(f"{_BULLET} [bold cyan]Memory Recalled[/bold cyan]")
        _console.print(f"{_NEST} [bold]✓ Full memory returned[/bold]")
        return content

    except Exception as e:
        return f"Error recalling memory: {e}"


@tool
def modify_memory(keyword: str, new_note: str) -> str:
    """
    Overwrite the note of an existing memory block (full replacement).
    Call recall_memory first to read current content before modifying.
    Args:
        keyword: label of the block to update
        new_note: replacement content for the block
    """
    try:
        keyword  = keyword.strip()
        new_note = new_note.strip()

        if not keyword or not new_note:
            return "Error: keyword and new_note must not be empty."

        content = _read_file()
        blocks  = _parse_blocks(content)

        if keyword not in blocks:
            return f"Error: '{keyword}' not found. Use save_memory to create it."

        new_block   = _build_block(keyword, new_note, int(time.time()))
        new_content = content.replace(blocks[keyword], new_block)
        _write_file(new_content)

        _console.print(f"{_BULLET} [bold cyan]Memory Modified[/bold cyan]")
        _console.print(f"{_NEST} [dim]{keyword}[/dim]")
        return f"✓ Memory updated: '{keyword}'"

    except Exception as e:
        return f"Error modifying memory: {e}"


@tool
def delete_memory(keyword: str) -> str:
    """
    Delete a memory block by keyword.
    Args:
        keyword: label of the block to delete
    """
    try:
        keyword = keyword.strip()

        if not keyword:
            return "Error: keyword must not be empty."

        content = _read_file()
        blocks  = _parse_blocks(content)

        if keyword not in blocks:
            return f"Error: '{keyword}' not found."

        new_content = content.replace(blocks[keyword], '')
        _write_file(new_content)

        _console.print(f"{_BULLET} [bold red]Memory Deleted[/bold red]")
        _console.print(f"{_NEST} [dim]{keyword}[/dim]")
        return f"✓ Memory deleted: '{keyword}'"

    except Exception as e:
        return f"Error deleting memory: {e}"


memory_tools = [save_memory, recall_memory, modify_memory, delete_memory]