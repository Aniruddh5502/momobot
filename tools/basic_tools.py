import sys, difflib, re
from datetime                       import datetime
from ddgs                           import DDGS
from pathlib                        import Path
from langchain_core.tools           import tool
from dotenv                         import load_dotenv
from bootstrap                      import WORKSPACE_DIR
from tools.response_handler         import create_tool_response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

workspace = WORKSPACE_DIR


from tools.write import write

@tool
def read(filePath: str) -> dict:
    """
    Read and return the contents of a file within the workspace.
    Returns file metadata (size, line count) to help the agent decide if the file is too large to process in one go.
    Args:
        filePath: Path to the file relative to the workspace (e.g. 'src/main.py')
    """
    try:
        target_path = (Path(workspace) / filePath).resolve()
        workspace_resolved = Path(workspace).resolve()

        try:
            target_path.relative_to(workspace_resolved)
        except ValueError:
            return create_tool_response(
                status="error",
                error_code="WORKSPACE_ESCAPE",
                error_message=f"The path '{filePath}' is outside the allowed workspace boundary.",
                recovery_hint="Ensure the path is relative to the workspace root."
            )

        if not target_path.exists():
            return create_tool_response(
                status="error",
                error_code="FILE_NOT_FOUND",
                error_message=f"The file '{filePath}' does not exist.",
                recovery_hint="Use listDir to verify the filename and path."
            )

        if not target_path.is_file():
            return create_tool_response(
                status="error",
                error_code="NOT_A_FILE",
                error_message=f"The path '{filePath}' is a directory, not a file.",
                recovery_hint="Use listDir to explore the contents of this directory."
            )

        stats = target_path.stat()
        file_size = stats.st_size

        if file_size > 1_000_000:
            return create_tool_response(
                status="warning",
                error_code="FILE_TOO_LARGE",
                error_message=f"File size ({file_size} bytes) exceeds the direct read limit.",
                recovery_hint="Consider writing a script to extract specific parts of the file or use a specialized tool if available.",
                data=None,
                metadata={"size_bytes": file_size, "state_delta": f"Read skipped — {file_size:,} bytes exceeds limit"}
            )

        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()

        line_count = len(content.splitlines())

        return create_tool_response(
            status="success",
            data=content,
            metadata={
                "filePath": filePath,
                "size_bytes": file_size,
                "line_count": line_count,
                "full_path": str(target_path),
                "state_delta": f"Read {filePath} ({line_count} lines, {file_size:,} bytes)",
            }
        )

    except UnicodeDecodeError:
        return create_tool_response(
            status="error",
            error_code="BINARY_FILE",
            error_message=f"The file '{filePath}' could not be decoded as UTF-8 text.",
            recovery_hint="This file is likely a binary. Do not attempt to read it as text."
        )
    except Exception as e:
        return create_tool_response(
            status="error",
            error_code="INTERNAL_READ_ERROR",
            error_message=str(e),
            recovery_hint="Check file permissions or try a different path."
        )


@tool
def edit(path: str, old_str: str, new_str: str) -> dict:
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
        return create_tool_response(
            status="error",
            error_code="MISSING_PATH",
            error_message="'path' is required.",
        )
    if old_str == "":
        return create_tool_response(
            status="error",
            error_code="EMPTY_OLD_STR",
            error_message="'old_str' cannot be empty.",
        )

    full_path = (Path(workspace) / path).resolve()
    workspace_resolved = Path(workspace).resolve()

    try:
        full_path.relative_to(workspace_resolved)
    except ValueError:
        return create_tool_response(
            status="error",
            error_code="OUT_OF_WORKSPACE",
            error_message=f"Path {path} is outside the workspace boundary.",
            recovery_hint="Ensure the path is relative to the workspace root.",
        )

    if not full_path.exists() or not full_path.is_file():
        return create_tool_response(
            status="error",
            error_code="NOT_A_FILE",
            error_message=f"'{path}' is not a file or does not exist.",
            recovery_hint="Use listDir or read to verify the file exists.",
        )

    original = full_path.read_text(encoding="utf-8")

    count = len(re.findall(re.escape(old_str), original))
    if count == 0:
        return create_tool_response(
            status="error",
            error_code="OLD_STR_NOT_FOUND",
            error_message=f"'old_str' not found in {path}. Make sure whitespace and indentation match exactly.",
            recovery_hint="Read the file again to confirm the exact text, then retry with the correct string."
        )
    if count > 1:
        return create_tool_response(
            status="error",
            error_code="MULTIPLE_INSTANCE_OF_SAME_STRING",
            error_message=f"'old_str' appears {count} times in {path}. It must be unique.",
            recovery_hint="Add more surrounding context to make the match unambiguous."
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
        return create_tool_response(
            status="error",
            error_code="NO_CHANGES",
            error_message="No changes made (old_str and new_str were identical).",
        )

    diff_output = "".join(diff_lines)
    return create_tool_response(
        status="success",
        data=f"✓ Edit applied to `{path}`\n\n```diff\n{diff_output}```",
        metadata={"state_delta": f"Edited {path}"},
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
    try:
        results = []
        with DDGS() as ddgsSearch:
            searchResults = ddgsSearch.text(query, max_results=numResults)

            if not searchResults:
                return create_tool_response(
                    status="error",
                    error_code="NO_RESULTS_FOUND",
                    error_message=f"No web results were found for the query: '{query}'.",
                    recovery_hint="Try broadening your search terms or using a different query."
                )

            for i, result in enumerate(searchResults, 1):
                results.append({
                    "index": i,
                    "title": result.get("title"),
                    "body": result.get("body"),
                    "href": result.get("href")
                })

        return create_tool_response(
            status="success",
            data=results,
            metadata={
                "query": query,
                "num_results_requested": numResults,
                "num_results_found": len(results),
                "state_delta": f"{len(results)} result(s) for '{query}'",
            }
        )

    except ImportError:
        return create_tool_response(
            status="error",
            error_code="MISSING_DEPENDENCY",
            error_message="The 'ddgs' package is not installed in the environment.",
            recovery_hint="Run 'pip install duckduckgo_search' to resolve this."
        )
    except Exception as e:
        return create_tool_response(
            status="error",
            error_code="INTERNAL_SEARCH_ERROR",
            error_message=str(e),
            recovery_hint="The search request failed. This could be due to rate limiting or network issues. Try again in a few minutes."
        )


@tool
def web_fetch(url: str) -> dict:
    """Fetch and extract text content from a webpage. Handles JS-rendered pages.

    Args:
        url: Full URL to fetch (e.g. 'https://example.com')
    """
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

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

        return create_tool_response(
            status="success",
            data=content,
            metadata={
                "url": url,
                "state_delta": f"Fetched {len(content):,} chars from {url}",
            }
        )

    except Exception as e:
        return create_tool_response(
            status="error",
            error_code="FETCH_FAILED",
            error_message=str(e),
            recovery_hint="The page may be blocking headless browsers, require authentication, or be temporarily unavailable. Try a different URL or use search instead."
        )


@tool
def listDir(dirPath: str = "") -> dict:
    """
    List files and directories in a folder within the workspace.
    Returns high-density metadata for each item to reduce verification turns.
    Args:
        dirPath:   Path relative to workspace root. Empty string lists workspace root.
    """
    try:
        fullPath = Path(workspace) / dirPath if dirPath else Path(workspace)

        if not fullPath.exists():
            return create_tool_response(
                status="error",
                error_code="DIR_NOT_FOUND",
                error_message=f"The path '{dirPath}' does not exist in the workspace.",
                recovery_hint="Use listDir with an empty string or a parent directory to explore the workspace structure."
            )

        if not fullPath.is_dir():
            return create_tool_response(
                status="error",
                error_code="NOT_A_DIRECTORY",
                error_message=f"The path '{dirPath}' is a file, not a directory.",
                recovery_hint="If you intended to read this file, use the read tool instead."
            )

        items = sorted(fullPath.iterdir())
        if not items:
            return create_tool_response(
                status="success",
                data=[],
                metadata={
                    "dirPath": dirPath,
                    "message": "Directory is empty",
                    "state_delta": f"{dirPath or '.'} is empty",
                }
            )

        results = []
        for item in items:
            stats = item.stat()
            results.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size_bytes": stats.st_size if not item.is_dir() else None,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
            })

        return create_tool_response(
            status="success",
            data=results,
            metadata={
                "dirPath": dirPath,
                "item_count": len(results),
                "full_path": str(fullPath),
                "state_delta": f"Listed {len(results)} item(s) in {dirPath or '.'}",
            }
        )

    except Exception as e:
        return create_tool_response(
            status="error",
            error_code="INTERNAL_ERROR",
            error_message=str(e),
            recovery_hint="This is an unexpected error. Try refreshing the directory or checking permissions."
        )


from tools.shell        import shell
from tools.taskState    import task_init
from tools.taskState    import task_clear
from tools.taskState    import task_replan
from tools.taskState    import task_update

base_tools = [edit, search, web_fetch, listDir, shell, read, write, task_init, task_update, task_replan, task_clear]