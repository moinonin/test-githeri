# Githeri Testbed & Autonomous Agent Worker Harness

Deterministic multi-agent testbed and showcase harness for [Githeri](https://github.com/nickrotich/githeri) — the Autonomous Software Factory for coding agents.

This directory provides isolated worker sandboxes (`<agent>-worker/`) for testing, benchmarking, and demonstrating end-to-end agentic full-stack generation.

---

## 🚀 Quickstart

### 1. Reinstall Latest Githeri Backend (Editable)
Sync the testbed with the latest backend code from the neighboring repository:
```bash
make update-githeri
```

### 2. Inspect Active Workers & Artifacts
```bash
make status
```

### 3. Factory Reset an Agent Worker
Reset any worker directory to clean factory defaults, seeded with root `AGENTS.md` and `.env`, and initialized:
```bash
make clean-hermes      # Factory reset hermes-worker
make clean-pi          # Factory reset pi-worker
make clean-opencode    # Factory reset opencode-worker
make clean-claude      # Factory reset claude-worker
```

Reset all workers at once:
```bash
make clean-all
```

---

## 🛠️ Complete Command Reference

| Command | Action |
| :--- | :--- |
| `make help` | Display interactive CLI help and targets table. |
| `make status` | Inspect active worker directories, spec count, plan count, and frontend presence. |
| `make clean-<agent>` | Factory reset `<agent>-worker/`, seed `AGENTS.md` and `.env`, run `githeri init --agent <agent>`. |
| `make reset-<agent>` | Alias for `make clean-<agent>`. |
| `make clean-all` | Clean and reset all registered agent workers. |
| `make update-githeri` | Reinstall latest local Githeri package (`-e ../ai/githeri`) into testbed environment. |

### Supported Agents
- `hermes` (Hermes Agent / NousResearch)
- `pi` (Pi Worker)
- `opencode` (OpenCode Agent)
- `claude` (Anthropic Claude Code)
- `cursor` (Cursor IDE Agent)
- `deepseek` (DeepSeek R1 / V3)
- `chatgpt` (OpenAI Codex / ChatGPT)
- `antigravity` (Google Antigravity CLI)

---

## 🔄 End-to-End Test Workflow

Run full-stack feature tests from prompt to working full-stack app in minutes:

### Step 1: Initialize Fresh Worker Sandbox
```bash
make clean-hermes
```

### Step 2: Navigate to Worker Directory
```bash
cd hermes-worker
```

### Step 3: Run Full-Stack Software Factory Command
Execute one single command to synthesize spec, generate implementation plan, extract UI contract, scaffold React + Tailwind v4 frontend, generate TypeScript API client, and dispatch the agent:

```bash
githeri start hermes "Build a FastAPI subscription billing API with Stripe webhooks, tier plans, and an interactive customer portal" --fullstack
```

> **Options:**
> - `--fullstack`: Synthesize backend contract + scaffold Vite/React frontend + compile API client.
> - `--frontend-dir <dir>`: Custom frontend workspace path (default: `frontend/`).
> - `--dry-run`: Preview synthesized spec, plan, and frontend scaffold without launching agent.

### Step 4: Verify Contract & Implementation

#### Verify Backend Contract (Zero Drift):
```bash
githeri verify
pytest -v
```

#### Verify Frontend Production Build:
```bash
cd frontend
npm run build
cd ..
```

### Step 5: Run Full-Stack Demo

#### Start Backend API Server:
```bash
uvicorn main:app --reload --port 8000
```
API Documentation: `http://localhost:8000/docs`

#### Start Frontend Dev Server:
```bash
cd frontend
npm run dev -- --port 5173
```
Web App UI: `http://localhost:5173`

### Step 6: Reset for Next Experiment
Return to root testbed and reset:
```bash
cd ..
make clean-hermes
```

---

## 📁 Directory Structure

```text
test-githeri/
├── Makefile              # Worker factory reset & status automation
├── README.md             # Harness runbook & command reference
├── AGENTS.md             # Root agent guidelines template seeded to workers
├── .env                  # Root API keys and environment variables
├── .gitignore            # Excludes node_modules, .venv, .env, DBs
│
├── hermes-worker/        # Isolated workspace for Hermes agent
│   ├── .githeri/         # Synthesized specs, plans, and audit logs
│   ├── frontend/         # Scaffolding Vite + React 18 + Tailwind v4 app
│   ├── main.py           # Generated FastAPI backend routes
│   └── test_main.py      # Automated contract verification test suite
│
├── pi-worker/            # Isolated workspace for Pi agent
└── opencode-worker/      # Isolated workspace for OpenCode agent
```

---

## 🔒 Git & Clean Repository Policy

Heavy dependencies and secrets are excluded from version control via `.gitignore`:
- `node_modules/` and `dist/`
- `.venv/` and `venv/`
- `.env` and `*.env.local`
- `*.db`, `*.sqlite`, `*.sqlite3`
- `.pytest_cache/` and `__pycache__/`

All worker directories maintain clean relative paths.
