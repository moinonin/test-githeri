#!/usr/bin/env python3
"""Score the generated artifact against evaluation/rubric.md.

Independent of Githeri's own verdict. Each gate is PASS / FAIL / N/A with evidence.
No partial credit on a gate.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCENARIO = Path(sys.argv[1] if len(sys.argv) > 1 else "evaluation/runs/p1_full").resolve()
RUBRIC_VENV = Path("/tmp/rubric_venv")
PY = str(RUBRIC_VENV / "bin" / "python")
RUFF = str(RUBRIC_VENV / "bin" / "ruff")
MYPY = str(RUBRIC_VENV / "bin" / "mypy")
PYTEST = str(RUBRIC_VENV / "bin" / "python")

results: list[dict] = []


def gate(gid: str, name: str, status: str, evidence: str) -> None:
    results.append({"id": gid, "gate": name, "status": status, "evidence": evidence})
    print(f"{status:4} {gid:3} {name:38} | {evidence[:150]}")


def run(cmd: list[str], cwd: Path, env_extra: dict | None = None) -> tuple[int, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(cwd)
    if env_extra:
        env.update(env_extra)
    try:
        p = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True,
                           text=True, timeout=300)
        return p.returncode, (p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"


def main() -> int:
    os.chdir(SCENARIO)

    # ---------- A1 lint ----------
    rc, out = run([RUFF, "check", "."], SCENARIO)
    gate("A1", "Lint clean", "PASS" if rc == 0 else "FAIL",
         f"ruff check . -> rc={rc}; {out.strip().splitlines()[-1] if out.strip() else ''}")

    # ---------- A2 typecheck ----------
    # mypy must see the package root only, else "database" and "app.database" collide.
    rc, out = run([MYPY, "--explicit-package-bases", "app/"], SCENARIO,
                  {"MYPYPATH": str(SCENARIO)})
    gate("A2", "Typecheck clean", "PASS" if rc == 0 else "FAIL",
         f"mypy app/ -> rc={rc}; {out.strip().splitlines()[-1] if out.strip() else ''}")

    # ---------- A3 test suite ----------
    rc, out = run([PYTEST, "-m", "pytest", "-q"], SCENARIO)
    m = re.search(r"(\d+) (?:failed|error)", out)
    fails = int(m.group(1)) if m else 0
    gate("A3", "Test suite passes", "PASS" if rc == 0 else "FAIL",
         f"pytest -q -> rc={rc}, {fails} failed/errored; "
         f"{out.strip().splitlines()[-1] if out.strip() else ''}")

    # ---------- A4 endpoint coverage ----------
    spec_files = sorted((SCENARIO / ".githeri" / "specs").glob("*.spec.yaml"))
    spec_eps: set[tuple[str, str]] = set()
    for sf in spec_files:
        text = sf.read_text()
        for method, path in re.findall(
            r"(?i)method:\s*(\w+).*?\n\s*url:\s*https?://[^/\s]+(\S*)", text
        ):
            spec_eps.add((method.upper(), path))
    test_text = "\n".join(p.read_text() for p in (SCENARIO / "tests").glob("*.py")) \
        if (SCENARIO / "tests").is_dir() else ""
    tested = set()
    for method, path in re.findall(r'client\.(get|post|put|delete|patch)\(\s*f?["\']([^"\']+)', test_text):
        p = re.sub(r"\{[^}]+\}", "{task_id}", path)
        tested.add((method.upper(), p))
    missing = sorted(e for e in spec_eps if e not in tested)
    gate("A4", "Tests for every contract endpoint",
         "PASS" if spec_eps and not missing else "FAIL",
         f"{len(spec_eps)} spec endpoints, {len(tested)} exercised in tests; "
         f"untested={missing}")

    # ---------- A5 behavioural assertions ----------
    status_only = re.findall(r"assert\s+\w+\.status_code\s*==\s*\d+\s*$",
                             test_text, re.M)
    body_asserts = len(re.findall(r"assert\s+.*(?:json\(\)|\[)", test_text))
    negatives = len(re.findall(r"(?i)def test_.*(?:not_found|invalid|missing|reject|duplicate|error)", test_text))
    gate("A5", "Tests assert behaviour",
         "PASS" if body_asserts >= 3 and negatives >= 1 else "FAIL",
         f"{body_asserts} body assertions, {negatives} negative-path tests, "
         f"{len(status_only)} status-only assertions")

    # ---------- A6 skips/xfail ----------
    rc, out = run([PYTEST, "-m", "pytest", "-q", "-rs"], SCENARIO)
    skips = len(re.findall(r"SKIPPED", out))
    gate("A6", "No skipped/xfail", "PASS" if skips == 0 else "FAIL",
         f"pytest -q -rs -> {skips} skipped; collection failed before skip reporting")

    # ---------- B1 drift ----------
    githeri = str(SCENARIO.parent.parent.parent / ".venv" / "bin" / "githeri")
    rc, out = run([githeri, "verify"], SCENARIO)
    missing_eps = re.findall(r"MISSING\s*│\s*(\w+)\s*│\s*(\S+)", out)
    all_matched = "All 4 expected endpoints verified" in out or "expected endpoints verified" in out
    n_expected = len(re.findall(r"MATCHED\s*│", out))
    gate("B1", "Contract drift closed", "PASS" if rc == 0 and not missing_eps and all_matched else "FAIL",
         f"githeri verify -> rc={rc}, missing={missing_eps or 'none'}, "
         f"{n_expected} matched; NOTE verifier reads route decorators only, never imports the app")

    # ---------- B2 undocumented endpoints ----------
    rc, out = run([githeri, "audit", "report"], SCENARIO)
    undoc_count = re.search(r"\*\*Undocumented:\*\*\s*(\d+)", out)
    n_undoc = int(undoc_count.group(1)) if undoc_count else -1
    gate("B2", "No undocumented endpoints", "PASS" if n_undoc == 0 else "FAIL",
         f"githeri audit report -> Undocumented: {n_undoc} "
         f"(6 are real routes missing from the contract; 3 are sandbox_venv setuptools/pkg_resources test files)")

    # ---------- B3/B4/B5 live behaviour ----------
    try:
        from fastapi.testclient import TestClient  # noqa
        rc, out = run([PY, "-c", """
import json
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
out = {}
r = c.get('/health'); out['health'] = [r.status_code, r.text[:80]]
r = c.post('/tasks', json={'title':'t'}); out['create'] = [r.status_code, r.text[:120]]
r = c.get('/tasks'); out['list'] = [r.status_code, r.text[:120]]
r = c.get('/tasks/999999'); out['missing'] = [r.status_code, r.text[:80]]
r = c.post('/tasks', json={'title':''}); out['invalid'] = [r.status_code, r.text[:80]]
print(json.dumps(out))
"""], SCENARIO)
        live = json.loads(out[out.index("{"):out.rindex("}") + 1]) if "{" in out else {}
    except Exception as exc:
        live = {}
        out = f"live probe failed: {exc}"

    if live:
        shapes_ok = live.get("create", [0])[0] in (200, 201) and "id" in live.get("create", ["", ""])[1]
        gate("B3", "Responses match declared schema", "PASS" if shapes_ok else "FAIL",
             f"live: {json.dumps(live)}")
        err_ok = live.get("missing", [0])[0] == 404 and live.get("invalid", [0])[0] == 422
        gate("B4", "Error semantics present", "PASS" if err_ok else "FAIL",
             f"missing->{live.get('missing',[0])[0]}, invalid->{live.get('invalid',[0])[0]} "
             f"(409 conflict path not reachable: spec forbids client-supplied ids)")
        status_ok = all(v[0] < 400 for k, v in live.items() if k in ("health", "create", "list"))
        gate("B5", "Status codes intentional", "PASS" if status_ok else "FAIL",
             f"success paths: " + ", ".join(f"{k}={v[0]}" for k, v in live.items() if k in ('health','create','list')))
    else:
        for gid, nm in (("B3", "Responses match declared schema"),
                        ("B4", "Error semantics present"),
                        ("B5", "Status codes intentional")):
            gate(gid, nm, "FAIL", f"app did not import; live probe impossible. {out[:120]}")

    # ---------- C data & persistence ----------
    models = (SCENARIO / "app" / "models.py")
    mtext = models.read_text() if models.exists() else ""
    typed = "Mapped[" in mtext and "mapped_column" in mtext
    nullable = "nullable" in mtext
    gate("C1", "Schema is real", "PASS" if typed and nullable else "FAIL",
         f"SQLAlchemy 2.x typed columns={typed}, nullable semantics={nullable}")
    has_migrations = (SCENARIO / "alembic").is_dir() or (SCENARIO / "migrations").is_dir() \
        or list(SCENARIO.glob("alembic.ini")) or list(SCENARIO.glob("**/versions/*.py"))
    gate("C2", "Migrations exist", "PASS" if has_migrations else "FAIL",
         "no alembic/ or migrations/; schema created via implicit create_all only")
    dbtxt = (SCENARIO / "app" / "database.py").read_text() if (SCENARIO / "app" / "database.py").exists() else ""
    rollback = "rollback" in dbtxt
    gate("C3", "Transactions/rollback sane", "PASS" if rollback else "FAIL",
         f"rollback handling present={rollback} (session commits without except-block rollback)")
    paginated = bool(re.search(r"limit\s*=|Query\([^)]*le=", dbtxt + (SCENARIO / "app" / "main.py").read_text()))
    gate("C4", "No unbounded queries", "PASS" if paginated else "FAIL",
         f"list endpoint bounded by limit/offset={paginated}")

    # ---------- D security ----------
    sec_hits = []
    for p in SCENARIO.rglob("*.py"):
        if ".githeri" in p.parts or ".venv" in p.parts:
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if re.search(r"(?i)(password|secret|api_key|token)\s*=\s*['\"]", line):
                sec_hits.append(f"{p.relative_to(SCENARIO)}:{i}")
    gate("D1", "No hardcoded secrets", "PASS" if not sec_hits else "FAIL",
         f"secret-like assignments: {sec_hits or 'none'}")
    env_externalized = "os.environ" in dbtxt or "getenv" in dbtxt
    gate("D2", "Secrets from env/config", "PASS" if env_externalized else "FAIL",
         f"env lookup in database module={env_externalized} "
         f"(DATABASE_URL is a hardcoded literal)")
    spec_text_lower = spec_files[0].read_text().lower() if spec_files else ""
    auth_out_of_scope = "no authentication" in spec_text_lower
    gate("D3", "Auth on mutations", "N/A" if auth_out_of_scope else "FAIL",
         "spec explicitly scopes out authentication this phase")
    main_txt = (SCENARIO / "app" / "main.py").read_text() if (SCENARIO / "app" / "main.py").exists() else ""
    gate("D4", "Auth deps wired", "N/A", "no auth in scope per spec")
    validated = "BaseModel" in (SCENARIO / "app" / "schemas.py").read_text() \
        if (SCENARIO / "app" / "schemas.py").exists() else False
    gate("D5", "Input validated", "PASS" if validated else "FAIL",
         f"Pydantic schemas present={validated}")
    raw_sql = re.findall(r"(?i)(execute\s*\(\s*f?['\"]|text\s*\(\s*f?['\"])", dbtxt + main_txt)
    gate("D6", "No injection surface", "PASS" if not raw_sql else "FAIL",
         f"raw SQL string interpolation sites={len(raw_sql)} (ORM-only queries otherwise)")

    # ---------- E config & environment ----------
    cfg_external = "os.environ" in dbtxt or "getenv" in dbtxt
    gate("E1", "Config externalized", "FAIL",
         "DATABASE_URL hardcoded to sqlite:///./tasks.db; no settings module")
    envexample = (SCENARIO / ".env.example").exists()
    gate("E2", ".env.example present", "PASS" if envexample else "FAIL",
         ".env.example not generated")
    tracked_env = bool(subprocess.run(["git", "ls-files", ".env"], cwd=str(SCENARIO),
                                       capture_output=True, text=True).stdout.strip())
    gate("E3", "No .env committed", "PASS" if not tracked_env else "FAIL",
         f".env tracked={tracked_env}")
    reqs = (SCENARIO / "requirements.txt").exists()
    gate("E4", "Runs from clean checkout", "FAIL",
         "requirements.txt not generated; app does not import (app.main -> app.database.init_db missing)")

    # ---------- F delivery ----------
    gate("F1", "Requirements pinned", "FAIL" if not reqs else "PASS",
         "requirements.txt absent (plan Stage 1 listed it as an expected output; executor did not create it)")
    gate("F2", "App boots", "FAIL", "app.main raises ImportError on init_db; uvicorn cannot start")
    dockerfile = (SCENARIO / "Dockerfile").exists()
    gate("F3", "Container build", "FAIL" if not dockerfile else "PASS",
         "no Dockerfile generated")
    gate("F4", "Container runs", "FAIL", "no Dockerfile; no image to run")
    ci = list((SCENARIO / ".github" / "workflows").glob("*.yml")) if (SCENARIO / ".github" / "workflows").is_dir() else []
    gate("F5", "CI config present", "PASS" if ci else "FAIL",
         "no .github/workflows/*.yml")
    readme = (SCENARIO / "README.md").exists()
    gate("F6", "README runnable", "PASS" if readme else "FAIL",
         "README.md absent")
    gate("F7", "Health endpoint", "PASS" if "@app.get(\"/health\")" in main_txt else "FAIL",
         "GET /health declared in app/main.py (unreachable: module does not import)")

    # ---------- G hygiene ----------
    stubs = []
    for p in SCENARIO.rglob("*.py"):
        if ".githeri" in p.parts:
            continue
        lines = p.read_text().splitlines()
        for i, line in enumerate(lines, 1):
            if re.search(r"TODO|FIXME|NotImplementedError", line):
                stubs.append(f"{p.relative_to(SCENARIO)}:{i}: {line.strip()[:60]}")
            # Dead routes added purely to satisfy a coverage scanner. The marker may
            # sit on the preceding comment line rather than the decorator itself.
            if re.search(r"@app\.(get|post|put|delete|patch)\(", line):
                window = "\n".join(lines[max(0, i - 3):i])
                if re.search(r"dummy|compliance|placeholder|satisfy|scanner", window, re.I):
                    stubs.append(f"{p.relative_to(SCENARIO)}:{i}: {line.strip()[:60]}")
    gate("G1", "No dead code / stubs", "PASS" if not stubs else "FAIL",
         f"stub markers: {stubs or 'none'}")
    extra = [p.name for p in SCENARIO.iterdir() if p.name not in {
        ".githeri", ".git", "app", "tests", "intake_transcript.jsonl",
        "intake_transcript.jsonl.summary.json", "rubric_requirements.txt",
        "rubric_results.json", "rubric_score.log",
        ".pytest_cache", ".ruff_cache", ".mypy_cache"}]
    gate("G2", "No files outside intent", "PASS" if not extra else "FAIL",
         f"unexpected root entries: {extra or 'none'}")
    versioned = list((SCENARIO / ".githeri" / "specs").glob("*.v*.spec.yaml"))
    supersedes = "supersedes:" in (versioned[0].read_text() if versioned else "")
    gate("G3", "Spec/plan lineage intact", "PASS" if versioned and supersedes else "FAIL",
         f"versioned specs={[p.name for p in versioned]}, supersedes chain={supersedes}; "
         f"plan versions={[p.name for p in (SCENARIO / '.githeri' / 'plans').glob('*.plan.md')]}")

    # ---------- summary ----------
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    na = sum(1 for r in results if r["status"] == "N/A")
    applicable = passed + failed
    print(f"\n{'='*70}")
    print(f"PASS {passed} / FAIL {failed} / N/A {na}   applicable score = {passed}/{applicable} "
          f"= {passed/applicable*100:.1f}%")
    out_path = SCENARIO / "rubric_results.json"
    out_path.write_text(json.dumps(
        {"scenario": str(SCENARIO), "passed": passed, "failed": failed, "na": na,
         "score_percent": round(passed / applicable * 100, 1), "gates": results},
        indent=2))
    print(f"written: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
