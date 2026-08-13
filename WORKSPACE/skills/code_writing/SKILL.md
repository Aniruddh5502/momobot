---
name: code_writing
description: Write high-reliability, deterministic code across C, C++, Python, and shell scripts. This skill implements the NASA/JPL "Power of Ten" rules for safety-critical systems. Trigger this skill for all coding tasks, especially those touching hardware, simulations, or critical data processing. Prioritize predictability and verifiability over cleverness or abstraction.
---

# Code Writing Skill: High-Reliability & Safety-Critical Standard

We do not write "scripts"; we build systems. Every line of code must be predictable, 
statically analyzable, and deterministic. We follow the **NASA/JPL Power of Ten** 
guidelines for all critical implementation.

---

## 🚀 The Safety-Critical Execution Loop

1. **Analyze** — Define atomic responsibilities. Identify all failure modes.
2. **Plan** — Map the call graph. Ensure it is acyclic. Define all fixed memory bounds.
3. **Implement** — Follow the strict rules below. No "quick drafts" in critical paths.
4. **Verify** — Compile with `-Wall -Wextra -Wpedantic`. Run static analyzers. 
5. **Audit** — Manually verify that no rule (1-10) was violated.

---

## 🛠 The "Power of Ten" Implementation Rules

These rules are **non-negotiable** for C/C++ and should be emulated in other languages.

### 1. Simple Control Flow
- **No `goto`**, no `setjmp`/`longjmp`.
- **No recursion** (direct or indirect). The function call graph must be acyclic.
- Use simple `if/else` and `switch` statements.

### 2. Fixed Loop Bounds
- Every loop must have a **statically provable upper bound**.
- No `while(true)` unless it's a system scheduler.
- Use `for` loops with explicit limits. If a limit is exceeded, trigger an assertion failure.

### 3. Zero Dynamic Memory (Post-Init)
- **No `malloc`, `free`, `new`, or `delete` after the initialization phase.**
- All memory must be allocated on the **stack** or as **static/global buffers**.
- Prevent heap fragmentation and non-deterministic allocation timing.

### 4. Atomic Function Length
- Max length: **60 lines** (roughly one printed page).
- One function = one logical unit. If it's longer, decompose it.

### 5. High Assertion Density
- Minimum **two assertions per function**.
- Assertions must be side-effect free Boolean tests.
- On failure: execute a recovery action (e.g., return `ERROR_CODE`).

### 6. Minimal Scope
- Declare data objects at the **smallest possible level of scope**.
- Prevent variable re-use for incompatible purposes.

### 7. Mandatory Return/Parameter Checking
- All non-void return values **must be checked**.
- All input parameters **must be validated** at the function entry.
- If a return value is intentionally ignored, cast to `(void)` with a justifying comment.

### 8. Restricted Preprocessor
- Limit to `#include` and simple macros.
- No token pasting, no variable argument lists (`...`), no recursive macros.
- Keep conditional compilation (`#ifdef`) to a minimum.

### 9. Pointer Restriction
- **Max one level of dereferencing** (no `int **ptr`).
- No function pointers.
- No pointers hidden in `typedef` or macros.

### 10. Zero-Warning Policy
- Compile with the most **pedantic settings** enabled.
- **Zero warnings** allowed. If the compiler is confused, rewrite the code to be trivially valid.
- Run at least one static analyzer daily.

---

## 🌐 Language-Specific Adaptations

### C / C++ (The Metal Standard)
- Strict adherence to the Power of Ten.
- Use `stdint.h` (e.g., `uint32_t`, `int16_t`) for explicit bit-width.
- No C++ STL containers that use the heap (e.g., no `std::vector` or `std::string` in critical loops). Use fixed-size arrays.

### Python (The Glue Standard)
Since Python is non-deterministic, use it **only** for non-critical tasks (plotting, data loading).
- **Emulate Rules**: Keep functions short ($\le$ 50 lines), use explicit type hints, and check all return values.
- **Avoid**: Deep recursion and complex dynamic abstractions.
- **Interface**: Use Python to call C-compiled binaries via `subprocess` or `ctypes` for critical math.

### Shell (The Tool Standard)
- Use `set -euo pipefail` for immediate failure on error.
- Validate all arguments at the start of the script.
- Avoid complex piping; use temporary files for intermediate data to allow auditing.

---

## ✅ Final Quality Audit Checklist

- [ ] **No Recursion**: Is the call graph acyclic?
- [ ] **Bounded Loops**: Does every loop have a fixed, provable limit?
- [ ] **No Heap**: Is `malloc`/`new` absent from the execution path?
- [ ] **Sizing**: Are all functions $\le$ 60 lines?
- [ ] **Assertions**: Are there $\ge 2$ checks per function?
- [ ] **Casting**: Are ignored return values explicitly cast to `(void)`?
- [ ] **Pointers**: Is there only one level of dereferencing?
- [ ] **Clean Build**: Did it compile with `-Wall -Wextra -Wpedantic` with **zero** warnings?
