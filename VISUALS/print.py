"""
print.py — Heading-aware smooth character printer for Momobot.

Features:
  - Markdown inline stripping: **bold**, *italic*, `code`, ~~strike~~
  - Heading detection: # / ## / ### → new line + styled prefix
  - LaTeX math token replacement inside $$ ... $$ and $ ... $ blocks
  - Smooth per-character streaming with configurable delay
  - Word-wrap at terminal width (whole words, no mid-word breaks)
"""

import sys
import time
import re
import shutil

# ── LaTeX → ASCII symbol map ──────────────────────────────────────────────────

LATEX_SYMBOLS: dict[str, str] = {
    r"\rightarrow":     "->",
    r"\leftarrow":      "<-",
    r"\Rightarrow":     "=>",
    r"\Leftarrow":      "<=",
    r"\leftrightarrow": "<->",
    r"\to":             "->",
    r"\gets":           "<-",
    r"\division":       "/",
    r"\div":            "/",
    r"\times":          "x",
    r"\cdot":           "·",
    r"\pm":             "±",
    r"\mp":             "∓",
    r"\leq":            "<=",
    r"\geq":            ">=",
    r"\neq":            "!=",
    r"\approx":         "≈",
    r"\equiv":          "≡",
    r"\infty":          "∞",
    r"\sum":            "Σ",
    r"\prod":           "Π",
    r"\sqrt":           "√",
    r"\partial":        "∂",
    r"\nabla":          "∇",
    r"\alpha":          "α",
    r"\beta":           "β",
    r"\gamma":          "γ",
    r"\delta":          "δ",
    r"\epsilon":        "ε",
    r"\theta":          "θ",
    r"\lambda":         "λ",
    r"\mu":             "μ",
    r"\pi":             "π",
    r"\sigma":          "σ",
    r"\phi":            "φ",
    r"\omega":          "ω",
    r"\forall":         "∀",
    r"\exists":         "∃",
    r"\in":             "∈",
    r"\notin":          "∉",
    r"\subset":         "⊂",
    r"\cup":            "∪",
    r"\cap":            "∩",
    r"\emptyset":       "∅",
    r"\therefore":      "∴",
    r"\because":        "∵",
    r"\ldots":          "...",
    r"\cdots":          "···",
}

_SORTED_LATEX = sorted(LATEX_SYMBOLS.keys(), key=len, reverse=True)


# ── Preprocessing passes ──────────────────────────────────────────────────────

def _replace_latex(text: str) -> str:
    """Replace LaTeX tokens inside $$ ... $$ and $ ... $ blocks."""
    def _sub_block(m: re.Match) -> str:
        inner = m.group(1)
        for token in _SORTED_LATEX:
            inner = inner.replace(token, LATEX_SYMBOLS[token])
        inner = re.sub(r"\\([A-Za-z]+)", lambda x: x.group(1), inner)
        return f"[{inner}]"

    # $$ must run before $ to avoid partial matches
    text = re.sub(r"\$\$(.*?)\$\$", _sub_block, text, flags=re.DOTALL)
    text = re.sub(r"\$(.*?)\$",     _sub_block, text, flags=re.DOTALL)
    return text


def _strip_markdown(text: str) -> str:
    """
    Remove inline Markdown formatting markers, keeping the inner text.
    Order matters: longer patterns first.
      ~~strikethrough~~  →  strikethrough
      **bold**           →  bold
      __bold__           →  bold
      *italic*           →  italic
      _italic_           →  italic
      `code`             →  code
    """
    # Strikethrough
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    # Bold (** and __)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__",     r"\1", text)
    # Italic (* and _) — single markers, not at word boundaries to avoid false hits
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def _preprocess(text: str) -> str:
    """Run all preprocessing passes in correct order."""
    text = _replace_latex(text)
    text = _strip_markdown(text)
    return text


# ── Heading helpers ───────────────────────────────────────────────────────────

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")

_HEADING_PREFIX = {
    1: "\n◆ ",
    2: "\n◇ ",
    3: "\n▸ ",
    4: "\n▹ ",
    5: "\n· ",
    6: "\n· ",
}


# ── Core emitters ─────────────────────────────────────────────────────────────

_scaler = 1.02


def _emit(ch: str, delay: float) -> None:
    sys.stdout.write(ch)
    sys.stdout.flush()
    if delay > 0:
        time.sleep(delay * _scaler)


def _emit_words(words: list[str], char_delay: float, width: int) -> None:
    """Emit words with whole-word wrapping at terminal width."""
    col = 0
    for word in words:
        if not word:
            continue
        space = 1 if col > 0 else 0
        if col > 0 and col + space + len(word) > width:
            _emit("\n", 0)
            col = 0
            space = 0
        if space:
            _emit(" ", char_delay)
            col += 1
        for ch in word:
            _emit(ch, char_delay)
        col += len(word)


# ── Public API ────────────────────────────────────────────────────────────────

def print_smart(text: str, char_delay: float = 0.01) -> None:
    """
    Stream `text` to stdout with:
      - Inline Markdown markers stripped (bold, italic, code, strikethrough)
      - LaTeX math substitution inside $$ / $ blocks
      - Heading lines (# through ######) rendered with a glyph prefix
      - Word-wrap at current terminal width
    Starts on the current line (no leading newline), ends with a single newline.
    """
    width = shutil.get_terminal_size(fallback=(80, 24)).columns
    text  = _preprocess(text)

    lines = text.split("\n")
    for line in lines:
        hm = _HEADING_RE.match(line)
        if hm:
            level  = len(hm.group(1))
            prefix = _HEADING_PREFIX.get(level, "\n· ")
            for ch in prefix:
                _emit(ch, 0)
            _emit_words(hm.group(2).split(" "), char_delay, width)
        else:
            _emit_words(line.split(" "), char_delay, width)
        _emit("\n", 0)