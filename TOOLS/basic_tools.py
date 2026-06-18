from langchain_core.tools import Tool
from pathlib import Path
import requests
from typing import Optional
import json
from rich.console import Console
import asyncio
from langchain_core.tools import BaseTool, Tool, tool
from dotenv import load_dotenv
import os
import re
from rich.markdown import Markdown
from VISUALS.animation import ThinkingAnimation
from setup import terracota, green_oli, cyan_blue, pink_purp, WORKSPACE_DIR

_console = Console()
_CORAL   = "#FF5F00"
# _BULLET  = f"[{_CORAL}]⬤[/{_CORAL}]"
_BULLET      =   "[grey66]✽ [/grey66]"
_NEST    = "[dim]  ⎿[/dim]"


@tool
def read_file(file_path: str) -> str:
    """Read and return the contents of a file.

    Args:
        file_path: Path to the file relative to workspace (e.g. 'src/main.py')
    """
    full_path = Path(WORKSPACE_DIR) / file_path

    if not full_path.exists():
        _console.print(f"{_BULLET} [bold red]Error[/bold red] [dim]- {file_path} not found[/dim]")
        return f"Error: File not found - {file_path}"

    if not full_path.is_file():
        _console.print(f"{_BULLET} [bold red]Error[/bold red]\n{_NEST} {file_path} is not a file")
        return f"Error: {file_path} is not a file"

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        _console.print(f"{_BULLET} [bold]Reading [/bold] [dim]{file_path}[/dim] [dim green]✓ DONE[/dim green]")
        return content
    except Exception as e:
        _console.print(f"{_BULLET} [bold red]Error[/bold red]\n{_NEST} {str(e)}")
        return f"Error reading file: {str(e)}"


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo.

    Args:
        query: Search query string
        num_results: Number of results to return (default 5)
    """
    try:
        from ddgs import DDGS
        _console.print(f"{_BULLET} [bold]Searching:[/bold] [dim]{query}[/dim]")

        results = []
        with DDGS() as ddgs_search:
            search_results = ddgs_search.text(query, max_results=num_results)

            if not search_results:
                _console.print(f"{_NEST} [yellow]No results found[/yellow]")
                return "No results found for the query."

            _console.print(f"{_NEST} [green]✓ Found {len(search_results)} results[/green]")

            for i, result in enumerate(search_results, 1):
                results.append(f"{i}. {result['title']}\n   {result['body']}\n   URL: {result['href']}\n")
        
        _console.print()
        return "\n".join(results)

    except ImportError:
        _console.print(f"{_BULLET} [bold red]Error[/bold red]: ddgs package not installed\n")
        return "Error: ddgs package not installed. Install with: pip install ddgs"
    except Exception as e:
        _console.print(f"{_BULLET} [bold red]Error[/bold red][red]{str(e)}[/red]")
        return f"Error during search: {str(e)}"


@tool
def web_fetch(url: str) -> str:
    """Fetch and extract text content from a webpage. Handles JS-rendered pages.

    Args:
        url: Full URL to fetch (e.g. 'https://example.com')
    """
    try:
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        _console.print(f"{_BULLET} [bold]Fetching URL[/bold] [dim]{url}[/dim]")

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

        _console.print(f"{_NEST} [bold]✓ Done ({len(content)} chars)[/bold]")
        return content

    except Exception as e:
        _console.print(f"{_BULLET} [bold red]Error[/bold red]\n{_NEST} {str(e)}")
        return f"Error fetching URL: {str(e)}"


@tool
def list_directory(dir_path: str = "") -> str:
    """List files and directories in a folder within the workspace.

    Args:
        dir_path: Path relative to workspace root. Empty string lists workspace root.
    """
    try:
        full_path = Path(WORKSPACE_DIR) / dir_path if dir_path else Path(WORKSPACE_DIR)

        if not full_path.exists():
            _console.print(f"{_BULLET} [bold red]Error[/bold red]\n{_NEST} Directory not found - {dir_path}")
            return f"Error: Directory not found - {dir_path}"

        if not full_path.is_dir():
            _console.print(f"{_BULLET} [bold red]Error[/bold red]\n{_NEST} {dir_path} is not a directory")
            return f"Error: {dir_path} is not a directory"

        items = sorted(full_path.iterdir())
        _console.print(f"{_BULLET} [bold]Listing Directory[/bold]\n{_NEST} [bold dim]{dir_path if dir_path else 'workspace root'}[/bold dim]")

        if not items:
            _console.print(f"{_NEST} [dim]Empty directory[/dim]")
            return f"Directory is empty: {dir_path}"

        results = []
        for item in items:
            if item.is_dir():
                _console.print(f"[bold dim]{_NEST} {item.name}/[/bold dim]")
                results.append(f" {item.name}/")
            else:
                _console.print(f"[bold dim]{_NEST} {item.name}[/bold dim]")
                results.append(f" {item.name}")

        _console.print()
        return "\n".join(results)

    except Exception as e:
        _console.print(f"{_BULLET} [bold red]Error[/bold red]\n{_NEST} {str(e)}")
        return f"Error listing directory: {str(e)}"

@tool
def write_file(file_path: str, content: str) -> str:
    """Write content to a file within the workspace. Creates parent directories if needed.
    
    Args:
        file_path: Path relative to workspace root (e.g. 'src/main.py')
        content: Text content to write to the file
    """
    try:
        full_path = (Path(WORKSPACE_DIR) / file_path).resolve()
        full_path.relative_to(Path(WORKSPACE_DIR).resolve())
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        _console.print(f"{_BULLET} [bold]Writing {file_path}[/bold] [green]DONE[/green]")
        return f"✓ {file_path} written successfully."

    except ValueError:
        return f"Error writing {file_path}: path escapes workspace ({WORKSPACE_DIR})"
    except Exception as e:
        _console.print(f"{_BULLET} [bold red]Error:[/bold red] {str(e)}")
        return f"Error writing {file_path}: {str(e)}"



load_dotenv()
API = os.getenv("Parser_API")
async def _parse_pdf_async(file_path: str, tier: str = "agentic") -> str:
    """Async PDF parsing using Llama Cloud API."""
    try:
        from llama_cloud import AsyncLlamaCloud
        _llama_client = AsyncLlamaCloud(api_key=API)
        file_obj = await _llama_client.files.create(file=file_path, purpose="parse")
        result = await _llama_client.parsing.parse(
            file_id=file_obj.id,
            tier=tier,
            version="latest",
            expand=["markdown_full", "text_full"],
        )
        return result.markdown_full or result.text_full or "No content extracted"
    except Exception as e:
        return f"PDF parsing failed: {str(e)}"


@tool
def parse_pdf(file_path: str, tier: str = "agentic") -> str:
    """Parse a PDF and return its content as markdown.
    file_path is relative to workspace (e.g. 'report.pdf' or 'papers/doc.pdf')
    tier options: fast, cost_effective, agentic, agentic_plus
    """
    full_path = Path(WORKSPACE_DIR) / file_path
    if not full_path.exists():
        full_path = Path(file_path)
    if not full_path.exists():
        return f"❌ File not found: {file_path}"
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(_parse_pdf_async(str(full_path), tier))
        finally:
            loop.close()
    except Exception as e:
        return f"❌ PDF parsing failed: {str(e)}"



from TOOLS.str_replace_tool       import  str_replace_tool
from TOOLS.persistant_shell_tool  import  bash_tool
from TOOLS.view_image             import  view_image_tool
from TOOLS.memory_tools           import  memory_tools
from TOOLS.clarification_tool     import  ask_clarifying_questions_tool
from TOOLS.task_state_tool        import  task_state_tools
from TOOLS.ocr_tool               import  ocr_tool
base_tools = [
    str_replace_tool, web_search, web_fetch, list_directory,
    bash_tool, read_file, write_file, view_image_tool,
    ask_clarifying_questions_tool, ocr_tool
] + memory_tools + task_state_tools
