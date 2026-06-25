import json
import tempfile
from pathlib import Path
import ollama
from pdf2image import convert_from_path
from langchain_core.tools import Tool
from rich.console import Console
from momo.WORKSPACE.output.momobot.bootstrap import WORKSPACE_DIR

_console = Console()
_CORAL  = "#FF5F00"
_BULLET = "✻ "
_NEST    = "[dim]   └─[/dim]"


def ocr_pdf(file_path: str, pages: list[int] | None = None) -> str:
    try:
        full_path = Path(WORKSPACE_DIR) / file_path
        if not full_path.exists():
            return f"Error: File not found: {file_path}"

        # Create output folder next to the PDF: e.g. CV.pdf → CV_ocr/
        output_dir = full_path.parent / (full_path.stem + "_ocr")
        output_dir.mkdir(parents=True, exist_ok=True)

        _console.print()
        _console.print(f"{_BULLET} [bold]OCR Tool[/bold]")
        _console.print(f"{_NEST} [dim]{file_path}[/dim]")
        _console.print(f"{_NEST} [dim]output → {output_dir.relative_to(WORKSPACE_DIR)}[/dim]")

        images = convert_from_path(str(full_path), dpi=70)

        if pages:
            selected = []
            for p in pages:
                if 1 <= p <= len(images):
                    selected.append((p, images[p - 1]))
                else:
                    _console.print(f"{_NEST} [yellow]Page {p} out of range, skipping[/yellow]")
        else:
            selected = list(enumerate(images, start=1))

        _console.print(f"{_NEST} Processing {len(selected)} page(s)…")

        saved_files = []
        for page_num, img in selected:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                img.save(tmp.name, format="JPEG", quality=95)
                tmp_path = tmp.name

            try:
                response = ollama.chat(
                    model="glm-ocr:q8_0",
                    messages=[
                        {
                            "role": "user",
                            "content": "Transcribe all text visible in this image exactly as it appears, preserving layout where possible.",
                            "images": [tmp_path],
                        }
                    ],
                    options={"num_ctx": 10240},
                )
                page_text = response["message"]["content"].strip()
            finally:
                Path(tmp_path).unlink(missing_ok=True)

            if not page_text:
                _console.print(f"{_NEST} [yellow]⚠ Page {page_num} returned empty response[/yellow]")

            # Save each page as its own .md file
            md_path = output_dir / f"page_{page_num:03d}.md"
            md_path.write_text(f"# Page {page_num}\n\n{page_text}\n", encoding="utf-8")
            saved_files.append(str(md_path.relative_to(WORKSPACE_DIR)))

            _console.print(f"{_NEST} [green]✓[/green] Page {page_num} → page_{page_num:03d}.md")

        _console.print(f"{_NEST} [bold]✓ OCR complete[/bold]")
        _console.print()

        rel_output_dir = str(output_dir.relative_to(WORKSPACE_DIR))
        return (
            f"OCR complete. {len(saved_files)} page(s) saved to: {rel_output_dir}/\n"
            f"Files: {', '.join(saved_files)}"
        )

    except Exception as e:
        _console.print()
        _console.print(f"{_BULLET} [bold red]OCR Error[/bold red]")
        _console.print(f"{_NEST} {str(e)}")
        _console.print()
        return f"Error during OCR: {str(e)}"

def _ocr_pdf_tool_func(input: str | dict) -> str:
    if isinstance(input, dict):
        data = input
    else:
        try:
            data = json.loads(input)
        except json.JSONDecodeError:
            # agent passed a bare file path string like "CV.pdf"
            data = {"file_path": input.strip()}
    return ocr_pdf(
        file_path=data["file_path"],
        pages=data.get("pages"),
    )

ocr_tool = Tool(
    name="ocr_pdf",
    func=_ocr_pdf_tool_func,
    description=(
        "Extract text from a PDF using OCR (vision model). "
        "Input: either a plain file path string (e.g. 'CV.pdf') or JSON with 'file_path' "
        "and optional 'pages' (list of 1-based page numbers; omit to process all pages). "
        "Saves each page as a .md file in a folder named '<pdf_stem>_ocr/' next to the PDF. "
        "Returns: output folder path and list of saved files."
    ),
)

