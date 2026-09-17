---
name: md-writing
description: "Use this skill whenever the user asks to write, create, save, or produce a document, note, report, guide, reference sheet, or any long-form written content that should be saved as a file. Triggers include: 'write a doc', 'make a note', 'create a report', 'save this as a file', 'write me a guide', 'make a reference sheet', 'document this', or any request where the deliverable is a standalone readable file rather than a conversational reply. Always use this skill when the output is meant to be kept, shared, or opened outside the chat — even if the request sounds casual."
---

## When to Create a `.md` File

Create a `.md` file (not inline text) when:

- The user asks to "write", "create", "make", "save", or "document" something
- The output is longer than ~20 lines
- The content is meant to be kept, shared, or referenced later
- The user says things like "for my notes", "I'll download it", "save this"

Do **not** create a file for:

- Conversational answers or explanations
- Short summaries the user will just read in chat
- Code snippets without surrounding documentation

---

## File Output Rules

- ask the user where to save it, if not specified then save to the respective working  directory in obsidian folder.
- Filename: lowercase, hyphen-separated, descriptive. Examples:
    - `robotics-kinematics-notes.md`
    - `python-async-guide.md`
    - `project-architecture-reference.md`
- After creating the file, always call `present_files` so the user can download it

---

## Document Structure

### Frontmatter (optional, use when helpful)

```
# Document Title

> One-line summary of what this document covers.

**Author:** (if relevant)  
**Date:** (if relevant)  
**Topic:** (if relevant)
```

### Heading Hierarchy

Use headings to create clear, navigable structure:

```
# H1 — Document title (one per file)
## H2 — Major sections
### H3 — Subsections
#### H4 — Sub-subsections (use sparingly)
```

Never skip levels (don't go from `##` to `####`).

### Standard Section Order

For technical/study documents:

1. Overview / What this covers
2. Core concepts (ordered from foundational to advanced)
3. Procedures / How-to steps
4. Reference tables / Quick lookup
5. Common mistakes / Pitfalls
6. Cheat sheet / Summary (last — for quick re-reads)

For guides and how-tos:

1. Goal / What you'll achieve
2. Prerequisites
3. Step-by-step instructions
4. Examples
5. Troubleshooting

---

## Writing Style Rules (The MIT OCW Standard)

**Core Mandate:** Write as if creating MIT OpenCourseWare materials. The goal is absolute clarity and conceptual transparency. Even a student struggling with the basics must be able to derive the "How" and "Why" from the text.

### Prose & Pedagogy
- **Directness:** Clear, direct sentences. No academic fluff or corporate hedging.
- **The "Why" First:** Never present a formula or a result without explaining the underlying intuition/logic first.
- **Socratic Flow:** Lead the reader from a known simple concept to a complex one. Do not jump levels.
- **Jargon Control:** Define every technical term on first use. If a term is complex, provide a plain-English analogy.
- **Active Voice:** Use active voice to describe processes (e.g., "The Jacobian maps..." instead of "It is mapped by the Jacobian...").

### Lists & Structuring
- **Bullet Lists:** Use for features, options, and pitfalls.
- **Numbered Lists:** Mandatory for sequential steps or logical derivations where order is critical.
- **Parallelism:** Keep list items grammatically consistent.
- **Nesting:** Max 2 levels deep to avoid cognitive overload.

### Tables & Data
- Use tables for comparisons, parameters, and lookup data.
- **Standard:** Header row mandatory. Use `:---` (left) or `:---:` (center) for alignment.
- **Comparison Tables:** Use these to contrast two similar but distinct concepts (e.g., Forward vs Inverse Kinematics) to highlight the exact difference.

### Code Blocks

Always specify the language for syntax highlighting:

````markdown
```python
def example():
    pass
```
````

For inline code, use backticks: `variable_name`, `command`, `filename.py`

### Math / Formulas

For documents with mathematical content, use LaTeX notation:

- Inline: `$formula$`
- Block: `$$formula$$`

<matrix writing> always use 
 - && -> column separator
 - \\ -> Line separator
$$
J = 
\begin{bmatrix} 
-l_1\sin(\theta_1) - l_2\sin(\theta_1 + \theta_2) && -l_2\sin(\theta_1 + \theta_2) \\
l_1\cos(\theta_1) + l_2\cos(\theta_1 + \theta_2) && l_2\cos(\theta_1 + \theta_2) 
\end{bmatrix}$$

### Callouts / Emphasis

Use blockquotes for tips, warnings, and important notes:

```markdown
> **Note:** This is an important clarification.

> **Warning:** This will overwrite existing files.

> **Tip:** Faster approach for basit cases.
```

Use **bold** for key terms on first introduction and critical warnings.  
Use _italics_ for emphasis, titles, and technical terms being defined.  
Don't overuse either — if everything is bold, nothing is.


## Completeness Checklist

Verify:
- [ ] Title is clear and specific (not just "Notes")
- [ ] All major sections are present and ordered logically
- [ ] No section is a wall of text — break up with subheadings, lists, or tables
- [ ] Code blocks have language tags
- [ ] Tables have aligned columns
- [ ] Key terms are bold on first use
- [ ] A summary or cheat-sheet section exists for reference documents
---

## Common Patterns by Document Type

### Study Notes
- Start with a one-line definition of the topic
- Cover concepts in dependency order (prerequisites before advanced)
- Include worked examples with step-by-step breakdowns
- End with a quick-reference table or cheat sheet
- Include "Common Mistakes" section — high exam value
- always show detailed worked out including math and explanation behind the decisions.
- No minimalism allowed.
- Always write concepts from the first principles to the last decisions and reasoning.

### API / Technical Reference
- One H2 per endpoint or function
- Parameters in a table: Name | Type | Required | Description
- Include a request and response example
- Note edge cases and error conditions

### How-To Guide

- State the goal in the first sentence
- List prerequisites before the steps
- Number every step
- Add code blocks for every command
- Include a "verify it worked" step

### Architecture / Design Document

- Start with a high-level summary diagram or description
- Explain _why_ decisions were made, not the what they are
- Cover data flow, component responsibilities, and interfaces
- Include a "Known Limitations" section


## Core Concepts

**Coroutine:** A function defined with `async def`. Must be awaited to run.

**Event Loop:** The runtime that schedules and runs coroutines.

**Task:** A coroutine wrapped to run concurrently via `asyncio.create_task()`.

---

## Basic Pattern

```python
import asyncio

async def fetch(url: str) -> str:
    await asyncio.sleep(1)  # simulate IO
    return f"result from {url}"

async def main():
    result = await fetch("https://example.com")
    print(result)

asyncio.run(main())
````

---

## Common Mistakes

|Mistake|Fix|
|:--|:--|
|Calling coroutine without `await`|Always `await` async functions|
|Blocking call inside async function|Use `asyncio.to_thread()` for blocking IO|
|Forgetting `asyncio.run()` at entry|Required to start the event loop|
