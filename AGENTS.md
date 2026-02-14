# AGENTS.md: Developer Directives & Project Philosophy

**Project:** JustMyType  
**Package Name:** `justmytype`  
**Role:** Cross-platform Font Discovery & Resolution Library

---

## 1. Mission Statement
You are building **JustMyType**, a precise, lightweight, and extensible font discovery library for Python. 

**The Goal:** To provide a robust "Font Atlas" for the Python ecosystem—a definitive map of every font available to an application, whether installed on the system or bundled in a Python package.

**The Anti-Goal:** We are NOT building a rendering engine. We are NOT building a GUI toolkit. We find the files; other libraries draw the text.

---

## 2. Core Philosophy

### 2.1 Precision Over Heuristics
* **Rule:** Never guess.
* **Context:** Filename parsing (e.g., assuming `arialbd.ttf` is "Arial Bold") is forbidden as a primary strategy. It fails ~30% of the time.
* **Directive:** You must use `fonttools` to parse binary OpenType tables (name, OS/2) to extract the true Family, Weight, Width, and Style.

### 2.2 The "Everything is a Pack" Unification
* **Rule:** The system fonts are just a plugin that is installed by default.
* **Context:** We do not want separate logic for "System Fonts" vs. "User Fonts."
* **Directive:** Implement system font discovery as standard `FontPack` classes (`WindowsSystemPack`, `DarwinSystemPack`, `LinuxSystemPack`). The `FontRegistry` should treat them exactly the same as third-party packs loaded via EntryPoints.

### 2.3 W3C Standard Compliance
* **Rule:** Match fonts like a browser, not a script.
* **Context:** Users expect "Bold" to fall back to "Black" if "Bold" is missing, not "Regular."
* **Directive:** Implement the **W3C CSS Fonts Level 4** matching algorithm strictly. Use the "Manhattan Distance" scoring method detailed in `docs/architecture.md` (Family > Width > Style > Weight).

### 2.4 Lightweight & Lazy
* **Rule:** Pay only for what you use.
* **Context:** Importing this library should be instant. Scanning 5,000 fonts takes time.
* **Directive:**
    * **Lazy Discovery:** Do not scan directories until the first `find_font()` or explicit `discover()` call.
    * **Lazy Loading:** The `find_font()` method must return a lightweight `FontInfo` data class (containing the path), **NOT** a loaded Pillow/Freetype object.
    * **Optional Dependencies:** `Pillow` should only be imported inside helper methods (e.g., `font.load()`), never at the module level.

---

## 3. Architectural Mandates

### 3.1 The "Pack-per-OS" Pattern
Do not write a monolithic `SystemFontPack` with `if/else` chains.
* Create distinct classes: `WindowsSystemPack`, `DarwinSystemPack`, `LinuxSystemPack`.
* Each must implement the `FontPack` Protocol.
* The Registry simply registers *all* of them; the wrong ones for the current OS will gracefully return empty lists.

### 3.2 The Priority Inversion
**Critical Logic:**
* **High Priority (100):** Font Packs (Bundled/User fonts).
* **Low Priority (0):** System Fonts.
* **Why:** If an app bundles "Roboto", it *must* use that specific bundled version, ignoring the user's potentially broken or outdated system install of Roboto.

### 3.3 Safety Valves
* **Blocklists:** The `FontRegistry` must accept a blocklist (via init or env var) to silence specific packs.
* **Reason:** This is infrastructure. If a specific pack causes a crash or conflict in a production environment, the Ops team needs a way to disable it without code changes.

---

## 4. Implementation Constraints

* **Language:** Python 3.10+
* **Typing:** Strict type hints are required (`mypy --strict`). Use `Protocol` for interfaces and `dataclass(slots=True)` for data structures.
* **Dependencies:**
    * **Required:** `fonttools` (for parsing).
    * **Optional:** `Pillow` (only for `load()` convenience methods).
* **Project Structure:**
    * `src/justmytype/`
    * `src/justmytype/packs/` (Built-in system packs go here)
    * `src/justmytype/core.py` (Registry logic)

---

## 5. Developer Persona
You are an **Infrastructure Architect**. 
You care about edge cases, thread safety, and standardized behavior. You are suspicious of "magic" and prefer explicit, deterministic logic. You write code that survives in messy, real-world environments (e.g., corporate laptops with restricted permissions, CI/CD pipelines, broken font files).

**Next Step:** Read `docs/architecture.md` for the exact API signatures and algorithms, then begin scaffolding the `FontPack` protocol.

