import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = "/Users/nickrotich/Desktop/portfolio/projects/python/test-githeri"
sys.path.insert(0, root)
for line in open(os.path.join(root, ".env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ[k] = v

import githeri.core.executor as ex

spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(root) / "evaluation/runs/fresh_mcp/.githeri/specs/support_followup_tasks_api.spec.yaml"
plan_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(root) / "evaluation/runs/fresh_mcp/.githeri/plans/support_followup_tasks_api.plan.md"
code_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(root) / "evaluation/runs/fresh_mcp"
max_attempts = int(sys.argv[4]) if len(sys.argv) > 4 else 2

constraint = (
    "\n\nHARD CONSTRAINTS (must follow exactly):\n"
    "- Implement the Task Manager domain from the spec/plan. Do NOT switch to a Todo domain.\n"
    "- Required endpoints: POST /tasks, GET /tasks, GET /tasks/{task_id}, "
    "PUT /tasks/{task_id}, DELETE /tasks/{task_id}, GET /health.\n"
    "- Use model names Task/TaskStatus, not Todo/TodoModel.\n"
    "- Create tests/test_tasks.py.\n"
)

original_generate = ex._generate_code_with_llm


def patched_generate(prompt, target_file, context_str, existing_content=None,
                     cumulative_context=None, provider=None, model=None,
                     previous_error=None):
    return original_generate(
        prompt + constraint,
        target_file,
        context_str,
        existing_content=existing_content,
        cumulative_context=cumulative_context,
        provider=provider,
        model=model,
        previous_error=previous_error,
    )


ex._generate_code_with_llm = patched_generate

python_bin = os.path.join(root, ".venv", "bin", "python")
githeri_bin = os.path.join(root, ".venv", "bin", "githeri")
repair_script = os.path.join(root, "evaluation", "scripts", "post_exec_repair.py")

for attempt in range(1, max_attempts + 1):
    print(f"\n=== Attempt {attempt}/{max_attempts} ===")
    # Clean generated app/tests but keep .githeri
    for sub in ("app", "tests"):
        p = code_dir / sub
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)

    try:
        report = ex.execute_plan(
            plan_path=plan_path,
            code_dir=code_dir,
            provider="gemini",
            model="gemini-flash-lite-latest",
            isolated=True,
            fallback_to_agent=True,
        )
    except Exception as exc:
        print("execute_plan raised:", exc)
        report = {"success": False, "errors": [str(exc)]}

    print("files_written:", report.get("files_written"))
    print("errors:", report.get("errors"))

    # Boot repair
    subprocess.run([python_bin, repair_script, str(code_dir), "app/main.py"], check=False)

    # Verify-exec
    verify_cmd = [
        githeri_bin, "verify-exec",
        "--spec", str(spec_path),
        "--plan", str(plan_path),
        "--code", str(code_dir),
        "--json",
    ]
    out = subprocess.run(verify_cmd, capture_output=True, text=True)
    try:
        data = json.loads(out.stdout)
    except Exception:
        data = {}
    print("verify-exec:", data.get("status"), data.get("score"))
    for layer in data.get("layers", []):
        print("  -", layer.get("name"), layer.get("status"), layer.get("errors"))

    # Tests
    test_proc = subprocess.run(
        [python_bin, "-m", "pytest", "-q"],
        cwd=str(code_dir),
        capture_output=True,
        text=True,
    )
    print("pytest exit:", test_proc.returncode)
    print(test_proc.stdout[-500:])

    verify_ok = data.get("status") == "success" and data.get("score", 0) >= 1.0
    tests_ok = test_proc.returncode == 0

    # Also run contract verify for drift
    verify_drift = subprocess.run(
        [githeri_bin, "verify", "-c", str(code_dir)],
        capture_output=True,
        text=True,
    )
    drift_ok = "Contract drift detected" not in verify_drift.stdout
    print("drift_ok:", drift_ok)

    if verify_ok and tests_ok and drift_ok:
        print("\nSUCCESS: all checks passed.")
        raise SystemExit(0)

    print("\nAttempt failed; retrying..." if attempt < max_attempts else "\nMax attempts reached; escalating to Path B.")

print("Escalating to Path B (manual/IDE agent).")
raise SystemExit(1)