# Feature

Name: add-health-endpoint
Purpose: Add a GET /health endpoint returning status ok

# Reference Specification
Structured YAML Task Specification (`add-health-endpoint`)

# Expected Deliverables
- Python source file `src/main.py` containing the FastAPI application and `/health` endpoint route.
- Automated or manual verification confirming that `GET /health` responds with HTTP 200 and `{"status": "ok"}`.

# Dependencies
- Python packages: `fastapi`, `pytest`, `httpx`

# Assumptions
- A Python environment with `pip` is available.
- The project root directory is initialized or will be set up to contain a `src/` directory.

---

# Global Success Criteria
- The FastAPI application builds and runs without error.
- `GET /health` returns an HTTP 200 status code.
- The response body for `GET /health` contains `ok`.
- All automated tests (`pytest tests/`) pass successfully.

---

# Execution Stages

## Stage 1: Create FastAPI Health Check Route

### Objective
Create the `src/main.py` file with the FastAPI application initialization and implement the `GET /health` route returning `{"status": "ok"}` to satisfy local goal L1.

### Inputs
- Target Environment: Python, FastAPI
- Business Rules: GET /health always returns 200 with JSON status ok

### Preconditions
- Target project directory exists.
- Required Python packages (`fastapi`, `pytest`, `httpx`) are installed in the active environment.

### Discovery Tasks
- Inspect project root directory structure to determine if `src/` directory exists.
- Inspect installed Python packages to confirm dependency availability.

### Execution Tasks
- Create the `src` directory if it does not already exist.
- Create or update `src/main.py` using the FastAPI blueprint pattern:
  - Import `FastAPI` from `fastapi`.
  - Initialize the `app = FastAPI()`.
  - Define an asynchronous route handler for `@app.get("/health")` that returns `{"status": "ok"}`.
- Inspect `src/main.py` to confirm the code structure matches the blueprint.

### Suggested Commands
```bash
python3 -c "import fastapi, pytest, httpx; print('Dependencies verified')"
mkdir -p src
touch src/main.py
```

### Expected Outputs
- `src/main.py` containing the `/health` endpoint definition.

### Local Verification
| Check | Command / Action | Expected |
|-------|------------------|----------|
| L1    | `test -f src/main.py && grep -q "/health" src/main.py` | Exit code 0 (file exists and contains `/health`) |

### Failure Procedure
If verification fails:
- Stop immediately.
- Diagnose whether `src/main.py` was created in the correct path or if content is missing.
- Correct the file contents and re-run verification.

### Completion Condition
Local Verification check L1 passes successfully.

---

## Stage 2: Verify GET /health Endpoint Behavior

### Objective
Start the FastAPI application and verify that `GET /health` successfully returns an HTTP 200 status code and a JSON body containing `ok` to satisfy local goal L2.

### Inputs
- `src/main.py`
- Running FastAPI server instance
- `httpx` / `pytest` / `curl` utilities

### Preconditions
- Stage 1 completed successfully (`src/main.py` exists and contains the health route).

### Discovery Tasks
- Inspect `src/main.py` to ensure ASGI app variable name (`app`) is correctly exposed.

### Execution Tasks
- Start the FastAPI development server in the background using `uvicorn` (or test via test client).
- Issue an HTTP `GET` request to `http://localhost:8000/health`.
- Validate the response status code and body content.
- Stop the background server process.

### Suggested Commands
```bash
# Start server in background (requires uvicorn)
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Run HTTP check
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health
curl -s http://localhost:8000/health

# Stop server
kill $SERVER_PID
```

### Expected Outputs
- HTTP status `200`
- Response body containing `"status": "ok"` or `"ok"`

### Local Verification
| Check | Command / Action | Expected |
|-------|------------------|----------|
| L2    | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` | `200` |
| L2    | `curl -s http://localhost:8000/health` | Output contains `ok` |

### Failure Procedure
If verification fails:
- Stop immediately.
- Check if `uvicorn` is installed and running correctly.
- Diagnose routing or syntax errors in `src/main.py`.
- Revise implementation and repeat Stage 2.

### Completion Condition
Local Verification checks for L2 pass successfully.

---

# Global Verification

Once every stage passes, perform complete project validation:

1. **Build / Import Verification**: Run Python syntax and import check on the codebase.
   ```bash
   python3 -m py_compile src/main.py
   ```
2. **Test Suite Execution**: Run the global verification command specified in the YAML spec.
   ```bash
   pytest tests/
   ```
3. **End-to-End Integration Check**: Spin up the application and confirm live HTTP request-response cycle matches all business rules.

Only after every global verification succeeds may the COMMAND_RUNWAY declare the feature complete.