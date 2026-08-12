---
name: mind-map
description: >
   Transform raw sources (PDFs, Web, Docs) into a high-density, self-curating Markdown Wiki. Use this skill whenever the user wants to build a knowledge base, organize research into a wiki, create a mind map of a subject, or manage a high-density information repository in the obsidian/ folder. This skill implements the MIT OCW Pedagogy Standard, ensuring information is structured for deep conceptual mastery.
---

# Fluid Knowledge Wiki — MIT OCW Pedagogy Engine

**Purpose:** Transform raw sources into high-density, first-principles Markdown Wikis that mirror the pedagogical depth of MIT OpenCourseWare (OCW).
**Philosophy:** Cognitive layering. Information density over metadata. Durable, interlinked artifacts. We do not simply summarize; we construct a scaffolded learning path that moves from intuitive physical reality to rigorous mathematical formalism.

---

## 📂 WORKSPACE ARCHITECTURE

All knowledge lives in `obsidian/`. The structure is a **Tree**, not a mesh.

```
obsidian/
├── mind_map.md                ← THE GLOBAL INDEX (Subject routing)
└── [Subject_Folder]/
    ├── mind_map.md             ← THE LOCAL INDEX (Topic routing)
    ├── [Topic_A].md            ← Cognitive Layered Content
    ├── [Topic_B].md            ← Cognitive Layered Content
    └── raw/
        └── [Source_Name].md    ← The base ingested document
```

---

## 🛠 THE EXECUTION PIPELINE (Orchestrator Workflow)

### Phase 1: Ingestion (Subagent Delegation)
1. **Goal:** Create the "Base File."
2. **Action:** Delegate to subagent to parse PDF or perform deep web research.
3. **Storage:** Save raw output to `obsidian/[Subject]/raw/[Source_Name].md`.

### Phase 2: The First-Principles Deconstruction
Before writing, the Orchestrator must decompose the topic into the following layers:
1. **The "Why":** The fundamental problem this concept solves. Why does this exist in the universe?
2. **The "How":** The mechanical/mathematical logic used to solve it.
3. **The "Wait, what?":** Common misconceptions, intuitive traps, or points of confusion for a student.
4. **The "Edge":** Boundary conditions, singularities, or regions where the theory breaks down.

### Phase 3: Dense Document Generation (The MIT OCW Standard)
Documents must follow this strict structural flow to ensure no "knowledge gaps" exist.

#### 1. The Intuitive Anchor (Plain Language)
- Start with a non-technical, conceptual explanation. 
- Use analogies. "Think of this as [X] doing [Y]."
- Explain the *physical reality* and the *behavioral intuition* before introducing a single equation.
- **MIT Standard Requirement:** The user should understand *what is happening* and *why it matters* before they are told *how to calculate it*. This removes the "formula-hunting" mentality and replaces it with "system-thinking."

#### 2. Formalism & Rigorous Derivation
- **Zero Gap Policy:** Every mathematical step must be shown. Do not say "it can be shown that..." or "simplifying, we get...". Show the actual simplification. If a step is skipped, it is a failure of the skill.
- **Immediate Definition:** Every symbol ($\alpha, \beta, \Sigma, \nabla$) must be defined in plain text immediately upon first appearance.
- **The Bridge:** Explicitly state the logical bridge: "Now that we understand the physical behavior of [X], we can represent it mathematically as [Equation]."
- **Notation Consistency:** Use standard academic notation throughout. If the source uses non-standard notation, convert it to the most widely accepted academic form and note the conversion.

#### 3. The "Physical Feel" (Intuition Check)
- Describe the sensitivity of the system. "If we increase the stiffness $k$, the frequency $\omega$ should logically increase because..."
- Provide a "Sanity Check" or "Back-of-the-Envelope" method to verify if a result makes physical sense without a calculator.
- **Limiting Behavior:** Discuss what happens when variables approach 0 or $\infty$. This is a hallmark of MIT-level physics/engineering notes.

#### 4. Application, Stress Testing & Comparison
- **The Standard Case:** A classic textbook example solved step-by-step.
- **The Edge Case:** A scenario where the logic reaches a limit or a singularity (e.g., Jacobian singularities in robotics, division by zero in fluid flow).
- **Comparative Analysis:** If multiple methods exist (e.g., Analytical vs. Numerical), create a detailed table comparing: *Computational Complexity, Accuracy, Convergence Speed, and Specific Use-cases*.

### Phase 4: Indexing (The Map)
1. **Local Map:** `obsidian/[Subject]/mind_map.md` $\rightarrow$ `[[File_Name]] --> Detailed one sentence description of its cognitive role.`
2. **Global Map:** Root `obsidian/mind_map.md` $\rightarrow$ `[[Subject_Folder]] --> High-level summary of the subject's scope.` (Append only).

---

## 📏 IMPLEMENTATION STANDARDS

- **Elaboration over Brevity:** Never sacrifice conceptual clarity for a shorter file. Use the space and tokens required to ensure the logic is airtight. If a point is nuanced, expand it. There is no penalty for length; there is only a penalty for shallowness.
- **No Academic Fluff:** Avoid phrases like "In this section, we will explore..." or "It is important to note that...". Remove the "AI wrapper." Provide direct, dense information.
- **Visuals:** Use Mermaid diagrams for flowcharts and logic paths. Use Tables for all comparative data.
- **Interlinking:** Every concept that appears in another file MUST be linked via `[[ ]]` to create a neural web of knowledge.
- **Verification:** Use `[⚠️ VERIFY: reason]` for any claim not explicitly backed by the source or a verified web search.
- **Preservation:** Never overwrite existing mind maps; append new nodes to maintain history.
- **Editing Protocol:** When a document doesn't need a wide rewrite, always use str_replace_file. For additions, use str_replace_file instead of write_file; if adding a section without deleting, include the previous line in the old_str and re-insert it in the new_str.

---

## 🔍 RETRIEVAL LOGIC (Tree Traversal)
1. `read_file("obsidian/mind_map.md")` $\rightarrow$ Subject Folder.
2. `read_file("obsidian/[Subject]/mind_map.md")` $\rightarrow$ Topic File.
3. `read_file("obsidian/[Subject]/[Topic_File].md")` $\rightarrow$ Content.
**NEVER `list_directory` to browse topics. Use the maps.**
