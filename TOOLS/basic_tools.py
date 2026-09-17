import sys, difflib, re
from datetime                       import datetime
from ddgs                           import DDGS
from pathlib                        import Path
from rich.console                   import Console
from rich.markup                    import escape
from langchain_core.tools           import BaseTool, Tool, tool
from dotenv                         import load_dotenv
from pathlib                        import Path
from VISUALS.animation              import ThinkingAnimation
from bootstrap                      import WORKSPACE_DIR
from TOOLS.response_handler         import create_tool_response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
console = Console()
_CORAL   = "#FF5F00"
theme_char      =   "✻"
_NEST    = "[dim]   └─[/dim]"

workspace = WORKSPACE_DIR
anim = ThinkingAnimation()

@tool
def read(filePath: str) -> dict:
    """
    Read and return the contents of a file within the workspace.
    Returns file metadata (size, line count) to help the agent decide if the file is too large to process in one go.
    Args:
        filePath: Path to the file relative to the workspace (e.g. 'src/main.py')
    """
    try:
        # 1. Security: Workspace Escape Protection
        target_path = (Path(workspace) / filePath).resolve()
        workspace_resolved = Path(workspace).resolve()
        
        try:
            target_path.relative_to(workspace_resolved)
        except ValueError:
            console.print(f"{theme_char} [dim red]Read failed: {filePath} escapes workspace[/dim red]")
            return create_tool_response(
                status="error",
                error_code="WORKSPACE_ESCAPE",
                error_message=f"The path '{filePath}' is outside the allowed workspace boundary.",
                recovery_hint="Ensure the path is relative to the workspace root."
            )

        # 2. Existence and Type Check
        if not target_path.exists():
            console.print(f"{theme_char} [dim red]Error: {filePath} not found.[/dim red]")
            return create_tool_response(
                status="error",
                error_code="FILE_NOT_FOUND",
                error_message=f"The file '{filePath}' does not exist.",
                recovery_hint="Use listDir to verify the filename and path."
            )

        if not target_path.is_file():
            console.print(f"{theme_char} [dim]{filePath} is not a file[/dim]")
            return create_tool_response(
                status="error",
                error_code="NOT_A_FILE",
                error_message=f"The path '{filePath}' is a directory, not a file.",
                recovery_hint="Use listDir to explore the contents of this directory."
            )

        # 3. High-Density Data Extraction
        stats = target_path.stat()
        file_size = stats.st_size
        
        # Safety check for massive files to avoid token overflow
        if file_size > 1_000_000: # 1MB limit for direct read
            console.print(f"{theme_char} [dim yellow]File {filePath} is too large for full read.[/dim yellow]")
            return create_tool_response(
                status="warning",
                error_code="FILE_TOO_LARGE",
                error_message=f"File size ({file_size} bytes) exceeds the direct read limit.",
                recovery_hint="Consider writing a script to extract specific parts of the file or use a specialized tool if available.",
                data=None,
                metadata={"size_bytes": file_size}
            )

        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        line_count = len(content.splitlines())
        console.print(f"{theme_char} [dim]Reading {filePath}[/dim]")
        
        return create_tool_response(
            status="success",
            data=content,
            metadata={
                "filePath": filePath,
                "size_bytes": file_size,
                "line_count": line_count,
                "full_path": str(target_path)
            }
        )

    except UnicodeDecodeError:
        console.print(f"{theme_char} [dim red]Error: {filePath} is not a text file.[/dim red]")
        return create_tool_response(
            status="error",
            error_code="BINARY_FILE",
            error_message=f"The file '{filePath}' could not be decoded as UTF-8 text.",
            recovery_hint="This file is likely a binary. Do not attempt to read it as text."
        )
    except Exception as e:
        console.print(f"{theme_char} [dim]Error reading file: {filePath} {str(e)}[/dim]")
        return create_tool_response(
            status="error",
            error_code="INTERNAL_READ_ERROR",
            error_message=str(e),
            recovery_hint="Check file permissions or try a different path."
        )

@tool
def search(query: str, numResults: int = 5) -> dict:
    """
    Search the web for information. 
    Returns a structured list of results including titles and URLs to allow the agent 
    to choose specific links for deeper reading.
    Args:
        query: The search query.
        numResults: Number of results to return (default: 5).
    """
    if anim: anim.start()
    try:
        results = []
        with DDGS() as ddgsSearch:
            searchResults = ddgsSearch.text(query, max_results=numResults)
            
            if not searchResults:
                console.print(f"{theme_char} Search: [dim]{query}[/dim][dim yellow]No results found[/dim yellow]")
                if anim: anim.stop()
                return create_tool_response(
                    status="error",
                    error_code="NO_RESULTS_FOUND",
                    error_message=f"No web results were found for the query: '{query}'.",
                    recovery_hint="Try broadening your search terms or using a different query."
                )
            
            for i, result in enumerate(searchResults, 1):
                # Store structured data instead of a pre-formatted string
                results.append({
                    "index": i,
                    "title": result.get("title"),
                    "body": result.get("body"),
                    "href": result.get("href")
                })
        
        if anim: anim.stop()
        console.print(f"{theme_char} Search: [dim]{query}[/dim]. Found: {len(results)}")
        
        return create_tool_response(
            status="success",
            data=results,
            metadata={
                "query": query,
                "num_results_requested": numResults,
                "num_results_found": len(results)
            }
        )
        
    except ImportError:
        if anim: anim.stop()
        console.print(f"{theme_char} [dim red]ddgs package not installed[/dim red]")
        return create_tool_response(
            status="error",
            error_code="MISSING_DEPENDENCY",
            error_message="The 'ddgs' package is not installed in the environment.",
            recovery_hint="Run 'pip install duckduckgo_search' to resolve this."
        )
    except Exception as e:
        if anim: anim.stop()
        console.print(f"{theme_char} [dim red]Error: {str(e)}[/dim red]")
        return create_tool_response(
            status="error",
            error_code="INTERNAL_SEARCH_ERROR",
            error_message=str(e),
            recovery_hint="The search request failed. This could be due to rate limiting or network issues. Try again in a few minutes."
        )

@tool
def web_fetch(url: str) -> str:
    """Fetch and extract text content from a webpage. Handles JS-rendered pages.

    Args:
        url: Full URL to fetch (e.g. 'https://example.com')
    """
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        console.print(f"{theme_char} [bold]Fetching URL[/bold] [dim]{url}[/dim]")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [l for l in text.splitlines() if l.strip()]
        content = "\n".join(lines)

        if len(content) > 8000:
            content = content[:10000] + "\n... [truncated]"

        console.print(f"{_NEST} [bold]✓ Done ({len(content)} chars)[/bold]")
        return create_tool_response(
            status="success",
            data=content,
            metadata={
                "url":url
            }
        )

    except Exception as e:
        console.print(f"{theme_char} [bold red]Error[/bold red]\n{_NEST} {str(e)}")
        return create_tool_response(
            status="error",
            error_message=str(e)
        )

@tool
def listDir(dirPath: str="") -> dict:
    """
    List files and directories in a folder within the workspace.
    Returns high-density metadata for each item to reduce verification turns.
    Args:
        dirPath:   Path relative to workspace root. Empty string lists workspace root.
    """
    _NEST    = "[dim]   └─[/dim]"
    try:
        fullPath = Path(workspace)/dirPath if dirPath else Path(workspace)
        
        # 1. Directory Existence Check
        if not fullPath.exists():
            console.print(f"{theme_char} [dim red]Directory not found: {dirPath}[/dim red]")
            return create_tool_response(
                status="error",
                error_code="DIR_NOT_FOUND",
                error_message=f"The path '{dirPath}' does not exist in the workspace.",
                recovery_hint="Use listDir with an empty string or a parent directory to explore the workspace structure."
            )
            
        # 2. Directory Type Check
        if not fullPath.is_dir():
            console.print(f"{theme_char} [dim red]{dirPath} is not a directory.[/dim red]")
            return create_tool_response(
                status="error",
                error_code="NOT_A_DIRECTORY",
                error_message=f"The path '{dirPath}' is a file, not a directory.",
                recovery_hint="If you intended to read this file, use the read tool instead."
            )
            
        items = sorted(fullPath.iterdir())
        console.print(f"{theme_char} [bold]Listing Directory[/bold]\n{_NEST} [bold dim]{dirPath if dirPath else 'workspace root'}[/bold dim]")
        
        if not items:
            console.print(f"{_NEST} [dim]Empty directory[/dim]")
            return create_tool_response(
                status="success",
                data=[],
                metadata={"dirPath": dirPath, "message": "Directory is empty"}
            )

        results = []
        for item in items:
            # Collect High-Density Metadata
            stats = item.stat()
            item_info = {
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size_bytes": stats.st_size if not item.is_dir() else None,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
            }
            
            # Console output for human observability
            type_indicator = "/" if item.is_dir() else ""
            console.print(f"[bold dim]{_NEST} {item.name}{type_indicator}[/bold dim]")
            results.append(item_info)

        return create_tool_response(
            status="success",
            data=results,
            metadata={
                "dirPath": dirPath,
                "item_count": len(results),
                "full_path": str(fullPath)
            }
        )
        
    except Exception as e:
        console.print(f"{theme_char} [dim red]Error: {str(e)}[/dim red]")
        return create_tool_response(
            status="error",
            error_code="INTERNAL_ERROR",
            error_message=str(e),
            recovery_hint="This is an unexpected error. Try refreshing the directory or checking permissions."
        )

@tool
def write(filePath: str, content: str) -> dict:
    """
    Writes text content to a file within the workspace. Creates parent directories if needed.
    Returns a verification snippet of the written content to eliminate the need for a subsequent read call.
    Args:
        filePath: Path relative to workspace root (e.g. 'src/main.py')
        content: Text content to write to the file
    """
    try:
        # 1. Security: Workspace Escape Protection
        target_path = (Path(workspace) / filePath).resolve()
        workspace_resolved = Path(workspace).resolve()
        
        try:
            target_path.relative_to(workspace_resolved)
        except ValueError:
            console.print(f"{theme_char} [dim red]Write failed: {filePath} escapes workspace[/dim red]")
            return create_tool_response(
                status="error",
                error_code="WORKSPACE_ESCAPE",
                error_message=f"The path '{filePath}' is outside the allowed workspace boundary.",
                recovery_hint="Ensure the path is relative to the workspace root and does not use '..' to climb out."
            )

        # 2. State Delta Calculation (New vs Updated)
        is_new = not target_path.exists()
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        # 3. Immediate Verification Snippet
        # We read back the last 100 characters or the whole file if it's smaller
        # to provide proof of success to the agent.
        with open(target_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
            snippet = full_text[-100:] if len(full_text) > 100 else full_text

        console.print(f"{theme_char} [dim]{filePath} written successfully[/dim]")
        
        return create_tool_response(
            status="success",
            data={"filePath": filePath, "bytes_written": len(content)},
            metadata={
                "state_delta": "File created" if is_new else "File updated",
                "verification_snippet": f"...{snippet}",
                "full_path": str(target_path)
            }
        )

    except PermissionError:
        console.print(f"{theme_char} [dim red]Write failed: Permission denied for {filePath}[/dim red]")
        return create_tool_response(
            status="error",
            error_code="PERMISSION_DENIED",
            error_message=f"Insufficient permissions to write to '{filePath}'.",
            recovery_hint="Check if the file is read-only or locked by another process."
        )
    except Exception as e:
        console.print(f"{theme_char} [dim red]Write failed: {filePath}. Error: {str(e)}[/dim red]")
        return create_tool_response(
            status="error",
            error_code="INTERNAL_WRITE_ERROR",
            error_message=str(e),
            recovery_hint="Check disk space or filesystem integrity."
        )

@tool
def edit(path: str, old_str: str, new_str: str) -> str:
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

    console.print(f"{theme_char} [bold]Editing File[/bold]")
    console.print(f"{_NEST} [dim]{path}[/dim]")

    for line in diff_lines:
        if line.startswith("---") or line.startswith("+++"):
            continue
        elif line.startswith("@@"):
            console.print(f"[dim]{escape(line)}[/dim]")
        elif line.startswith("-"):
            console.print(f"[red]{escape(line)}[/red]")
        elif line.startswith("+"):
            console.print(f"[green]{escape(line)}[/green]")
        else:
            console.print(escape(line))

    console.print()

    diff_output = "".join(diff_lines)
    return f"✓ Edit applied to `{path}`\n\n```diff\n{diff_output}```"


from TOOLS.edit                     import  edit
from TOOLS.shell                    import  shell
from TOOLS.view                     import  view
from TOOLS.taskState                import  task_init
from TOOLS.taskState                import  task_clear
from TOOLS.taskState                import  task_replan
from TOOLS.taskState                import  task_update
from TOOLS.ocr_tool                 import  ocr_tool

base_tools = [
    edit, search, web_fetch, listDir, shell, read, write,
    task_init, task_update, task_replan, task_clear
]


from typing import Any, Dict
def testTool(name:tool, input:dict=None):
    result = name.invoke(input)
    if result["status"]=="success":
        console.print(f"{theme_char} [dim]{name.name}[/dim] [green]PASSED[/green] TEST")
    else:
        console.print(f"{theme_char} [dim]{name.name:^40}[/dim] [red]FAILED[/red] TEST")
    pass
if __name__ == "__main__":
    # Test for List dir
    testTool(name=listDir,input={"dirPath":""})