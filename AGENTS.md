# Autonomous Agent Operational Guidelines (`AGENTS.md`)

This repository is governed by strict agent operational rules designed for autonomous coding agents (Antigravity, Cursor, Claude Code, Gemini CLI, Codex, Hermes, Pi, etc.).

---

## 🔒 1. Strict Privacy & Path Safety: No Absolute User Paths
- **Never hardcode absolute host paths or user home directories** (`/Users/<username>/...`, `/home/<username>/...`, `C:\Users\<username>\...`).
- **Always use repository-relative paths** (`src/main.py`, `tests/test_api.py`, `docs/runbook.md`, `frontend/src/App.tsx`).
- Markdown links must use relative references: `[Label](path/to/file.py)` or `[Label](path/to/file.py#L10-L20)`. Never prefix with `file:///Users/...`.
- In test scripts and modules, resolve roots dynamically using `Path(__file__).resolve().parent`.

---

## 📐 2. Contract-First Development (The Githeri Protocol)
Before writing or modifying backend code, always verify the active contract specification to prevent route drift, broken schemas, and multi-turn hallucination loops:

1. **Inspect Active Specifications & Plans**:
   - Check `.githeri/specs/*.spec.yaml` for expected endpoints, HTTP methods, headers, and schemas.
   - Check `.githeri/plans/*.plan.md` for phased task checklists.
   - If no plan or spec exists for a new feature, synthesize them:
     ```bash
     githeri plan "<natural language feature request>"
     ```
     Or call the `githeri_plan(prompt="...")` MCP tool directly in your agent session.

2. **Production-Grade Implementation (Zero Simplifications)**:
   - **Never simplify or water down requirements** because a task or file seems "complex".
   - **Never say** "this is too complex, let me simplify it" or produce a "clean/simplified" version.
   - **Never replace** real cryptographic, authentication, database, or business logic with stubs or shortcuts.
   - Implement the complete production specifications as contracted. Simplification is considered a failure.

3. **No Placeholders or Stubs**:
   - **Never write placeholder functions**, stubs, `pass`, or `...`.
   - **Never write dummy returns** like `return {} if __name__ else {}`.
   - Every file written must be 100% complete, syntactically valid, and operational.

4. **Phased Execution**:
   - **Phase 1: Schemas & Database Models** (Declare tables, migrations, constraints).
   - **Phase 2: Routes & Controllers** (Mount endpoints matching the exact spec paths and HTTP verbs).
   - **Phase 3: Automated Verification Tests** (Unit and integration tests).

5. **Surgical Splicing & AST Grounding**:
   - When modifying existing codebases, **do not regenerate entire files**.
   - Target the specific class, function, or route handler and surgically apply changes to prevent import regression and code loss.

---

## 🛡️ 3. Execution & Process Safety: No Blocking Daemons or Log Watchers
- **Never start blocking servers in the background or foreground** (`uvicorn`, `flask run`, `python -m http.server`, `sleep`, or `curl` test loops).
- **Never run blocking log-watching commands** (`tail -f`, continuous stream monitoring).
- **Never leave background server processes running**. If an ephemeral server process is ever started for quick health verification, you MUST kill its PID (`kill -9 $PID`) before the command or turn ends.
- **Always verify routes and logic in-memory** using `githeri verify` or `pytest` with `TestClient` / `AsyncClient`.

---

## 🎨 4. Full-Stack & Frontend Operational Rules (`frontend/`)
When generating or modifying frontend code in full-stack projects:

1. **Static Verification Only (NEVER Run Dev Servers)**:
   - **NEVER execute `npm run dev`**, `vite`, `npm start`, or `next dev`. Dev servers block the terminal process and hang agent execution indefinitely.
   - Always verify frontend changes statically:
     ```bash
     cd frontend && npm run build
     ```
   - Both TypeScript type-checking (`tsc -b`) and Vite production bundling must exit cleanly with code 0.

2. **Zero Hardcoded Localhost URLs**:
   - **NEVER hardcode `http://localhost:8000`** or `http://127.0.0.1:8000` inside frontend components.
   - Always import and use the scaffolded, type-safe API client:
     ```typescript
     import { apiClient } from './api/client'
     ```
   - For custom endpoints, resolve from environment with relative fallbacks:
     ```typescript
     const API_BASE = import.meta.env.VITE_API_URL || ''
     ```

3. **Live Contract Binding (No Mock Data Arrays)**:
   - **NEVER leave fake mock data arrays** (`const MOCK_ITEMS = [...]`) in production views.
   - Wire all UI views (lists, tables, modals, forms, and detail drawers) to real backend routes via `apiClient`.
   - Every data-fetching view MUST handle:
     - **Loading State**: Spinners or skeleton loaders while awaiting response.
     - **Empty State**: Clear placeholder message and creation CTA when list/table is empty.
     - **Error State**: User-facing banner or toast on network/HTTP errors.

4. **Component Surgery & Modern CSS Integrity**:
   - Maintain modern Tailwind CSS v4 styling: keep `@tailwindcss/vite` in `vite.config.ts` and `@import "tailwindcss";` in `src/index.css`.
   - **NEVER create obsolete `tailwind.config.js`** or conflicting PostCSS configs that break Vite v4 builds.
   - Use Lucide icons (`lucide-react`) for consistent UI iconography.
   - Do not regenerate entire component trees; isolate and update the target component.

---

## 🏗️ 5. Canonical Module Structure & Code Hygiene
- **Framework Singleton**: In framework entrypoints (e.g., `main.py`), instantiate the application instance (`app = FastAPI(...)`) at module scope. Never hide it inside factory functions if route decorators are applied at module level.
- **Declarative Database Models**: Always declare base models at module level (`Base = declarative_base()`). Never set `Base = None` or defer model base declaration.
- **Complete Imports**: Every type hint and framework symbol must be explicitly imported:
   - Python typing: `from typing import Optional, Final, AsyncGenerator, List, Dict, Tuple`
   - Framework primitives: `from fastapi import Depends, HTTPException, status, APIRouter`
   - React hooks: `import { useState, useEffect, useCallback } from 'react'`
- **Static Defect Gate**: Run static defect checks before finishing:
   ```bash
   ruff check --select F821 <modified_file>
   python -m py_compile <modified_file>
   ```

---

## 🚦 6. Dual Pre-Completion Verification Gate
Before completing any task or ending your turn:
1. **Backend Contract Verification**:
   ```bash
   githeri verify
   pytest -v
   ```
   - Automatically runs static defect analysis (Ruff F821 for undefined names).
   - Verifies route contract parity against `.githeri/specs/`.
   - Validates module boot and clean imports.
   - Executes the automated test suite in-memory without background server daemons.
2. **Frontend Production Build Gate** (if `frontend/` directory exists):
   ```bash
   cd frontend && npm run build
   ```
   - Validates TypeScript types (`tsc -b`).
   - Validates JSX syntax and component exports.
   - Compiles production assets into `frontend/dist/`.
3. If either gate reports missing endpoints, syntax errors, or build failures:
   - Fix the code implementation until all checks pass.
   - Do NOT modify or dilute the contract spec unless explicitly instructed by the user.
4. A task is only complete once BOTH verification gates exit with code 0.
