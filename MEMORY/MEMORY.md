## identity
timestamp: 1749513600
Full name: Aniruddho Biswas Badhon. Goes by Ani. Mechanical Engineering graduate from BUET (Bangladesh University of Engineering and Technology), student ID 2010117. Supervised by Prof. Abu Rayhan Md. Ali. Thesis defended June 2026.

---

## personality
timestamp: 1749513600
Communicates tersely and directly. Corrects imprecision immediately. Prefers concise honest assessments over hedged ones. Dislikes over-engineered solutions and unnecessary documentation. Uses :333 as a pleased/agreeing emoticon. Interdisciplinary self-directed learner — accumulates knowledge based on what needs to be built, not by fitting problems to a chosen field. High-throughput idea generation is baseline expectation for himself. Treats documentation as infrastructure for output, not preservation of rare insights. Pragmatic skepticism toward institutional narratives and academic funding structures.

---

## expertise
timestamp: 1749513600
Spans mechanical engineering, embedded systems, ML, information theory, and defense R&D. Primary language: Python. Secondary: C/C++. Libraries: numpy, matplotlib, pandas. Prefers Mermaid diagrams over ASCII art. Preferred response style: direct, concise, table-based where appropriate.

---

## thesis
timestamp: 1749513600
B.Sc. thesis: surrogate-assisted design framework for multi-objective parameter optimization of a MEMS accelerometer. 20-member ensemble neural network ROM trained on ~2000 ANSYS FEM simulations. 4 geometric inputs: beam height, width, length, fillet size. 10 structural outputs: modal frequencies, deformation, stress. Uniform grid sampling for full design space coverage. Intentional overfitting to prevent mode-swapping artifacts (bounded interpolator, not generalizer). GPR rejected on O(n³) grounds. PCA-confirmed 2–3 PC convergence justified manifold visualization. Jacobian sensitivity and UMAP manifold for validation. Thesis built with LaTeX (cover.tex, frontmatter.tex, \include{} workflow). Presentation built with Python/pptxgenjs pipeline.

---

## momobot
timestamp: 1781529486
Local LLM agent. Stack: Ollama (model gemma4:31b-cloud, 262K context), LangGraph + LangChain, Ubuntu 22.04.5 LTS (bash). Hardware: ASUS VivoBook X515MA, Intel Celeron N4020 @ 1.10GHz, 4GB RAM. Graph structure: USER_INPUT → REASONING → TOOL_NODE → COMPACT. Memory is implemented as a persistent flat-file semantic store (MEMORY.md) with CRUD tools (save, recall, modify, delete). Compaction is token-based: triggers when prompt_eval_count exceeds 100k, summarizing older messages into a session state summary while keeping a recent window of messages. Setup via setup.py with relative paths. System prompt composed of SOUL.md, USER.md, and SKILL.md, wrapped with the current memory state.

---

## momobot_tools
timestamp: 1781116500
Tools use @tool decorator pattern with typed signatures. Includes: write_file, read_file, web_search (ddgs), web_fetch (Playwright headless for 403 bypass), list_directory, str_replace_tool, persistent_shell_tool (pwsh.exe, sentinel-delimited I/O, blocklist guards write ops), view_image (calls vision model via ollama.chat(), returns plain text), ocr_tool (glm-ocr, 70 DPI for text docs, outputs per-page .md files). Memory tools handle raw text manipulation of MEMORY.md via regex parsing of ## headers.

---

## momobot_ui
timestamp: 1749513600
Rich console. prompt_toolkit multiline input (escape+enter to submit). ThinkingAnimation spinner with _stopped guard. print_smart with heading detection and LaTeX symbol substitution.

---

## momobot_subagent
timestamp: 1749513600
Lacks the complex memory cascade of the main agent; uses a standard context window for tool-based tasks. task_complete is the only valid exit signal. Continuation HumanMessage injected when no tool call detected. GraphRecursionError caught as hard failure.

---

## cerberus
timestamp: 1749513600
Fault-tolerant ESP32 flight controller firmware. Project: Cerberus / DhumketuX contribution. Triple OTA partition layout (ota_0/1/2, each 1280KB). SHA256 + CRC32 verification. Self-repair engine with erase-write-verify sequencing. Running partition protection. Round-robin failover. Hardware watchdog (TWDT, trigger_panic=true). 2-layer 9-copy variable TMR with median fallback. Process TMR via volatile + compiler barriers. Python build/flash pipeline. Rated 8.6/10 for BD defense hiring context. Framing: "reliability engineering" / "fault-tolerant systems" over firmware/embedded terminology.

---

## career
timestamp: 1749513600
Actively job-searching as of June 2026. Pending application to glafit Bangladesh Ltd. (Japanese EV micromobility startup in Dhaka) for Executive (Service & Installation) role — sent to harich@glafit.com with tailored LaTeX CV and formal email. Minimum salary threshold ~60,000 BDT. Negotiation starting point: 80,000–100,000 BDT. Portfolio: aniruddh5502.github.io/Portfolio/. Considering Anthropic application after Momobot upgrades + proper CV repackaging — target roles: ML infra, agent tooling, research engineering, eval systems.

---

## projects_portfolio
timestamp: 1749513600
Key projects: Momobot (LLM agent, custom memory compaction, subagent orchestration), Cerberus (fault-tolerant embedded firmware, TMR), MEMS surrogate model (multi-output MLP ensemble, uncertainty quantification, Jacobian reconstruction via exported sklearn weights), ASHRAE-grant-winning Spiral Plate Heat Exchanger, COLMAP-Based 3D Mesh Reconstruction. LDPC corruption rate: 0.36%.

---

## cat_manager
timestamp: 1749513600
New project: AI agentic task manager that replaces human managers. MVP: 2 teammates with MD profile files. Agent loop triggered by any message via timers/hooks. Handles task decomposition, assignment, marking done with auto-logs, state updates. All project/rules/policies in MD files. Stack: LangGraph (Momobot-derived) + Claude API.

---

## langgraph_patterns
timestamp: 1749513600
add_messages reducer handles accumulation within invoke() but not across separate calls (requires persistent_state carried across turns). ToolNode must be passed directly, not wrapped in lambda, for config propagation. Recursion limit formula: MAX_ITERATIONS * 3 + 10 for 3-node graph. State sync block must be inside inner node output loop. SystemMessage must not be in initial persistent_state — inject in reasoning_node via build_system_prompt().

---

## financial_interest
timestamp: 1749513600
Expressed interest in financial knowledge-building as a long-term generational trajectory goal. Views AI labor dynamics, open-source vs. closed-model power structures critically. Has direct building experience that grounds skepticism about multi-agent reliability claims.

---
## tool_test_2026
timestamp: 1786538417
Verified toolset functionality on June 9, 2026.

---

