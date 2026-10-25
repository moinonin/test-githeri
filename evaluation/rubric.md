# Production-Grade Rubric

Scored independently of Githeri's own verdict. Githeri verifies contract coverage; this rubric
verifies software quality. The gap between the two is the headline finding of the evaluation.

Each gate is PASS / FAIL / N/A with evidence. No partial credit on a gate.

## A. Correctness & verification

| # | Gate | Command | Pass condition |
|---|---|---|---|
| A1 | Lint clean | `ruff check .` | exit 0, zero findings |
| A2 | Typecheck clean | `mypy src/` (or `pyright`) | exit 0, zero errors |
| A3 | Test suite passes | `pytest -q` | exit 0, 0 failures |
| A4 | Tests exist for every contract endpoint | endpoint list from spec vs test names | every method+path in spec has ≥1 test |
| A5 | Tests actually assert behaviour | read test bodies | no test that only asserts status code on a wrong-shaped response; ≥1 negative-path test per endpoint family |
| A6 | No skipped/xfail hiding failures | `pytest -q -rs` | zero skipped, zero xfail |

## B. API & contract

| # | Gate | Command | Pass condition |
|---|---|---|---|
| B1 | Contract drift closed | `githeri verify` | exit 0, 0 missing endpoints |
| B2 | No undocumented endpoints | `githeri audit report` | `undocumented_endpoints == []` |
| B3 | Responses match declared schema | manual read + one live request | status code, body shape, and error shape match spec |
| B4 | Error semantics present | live requests | invalid input → 422, missing resource → 404, conflict → 409 — and each is covered by a test |
| B5 | Status codes are intentional | live requests | no endpoint returns 200 for a failure condition |

## C. Data & persistence

| # | Gate | Command | Pass condition |
|---|---|---|---|
| C1 | Schema is real | read models | entities have typed fields, PK, constraints, and nullable semantics |
| C2 | Migrations exist | `alembic/` or equivalent | schema changes are versioned, not implicit `create_all` only |
| C3 | Transactions/rollback sane | read session code | commit on success, rollback on exception |
| C4 | No N+1 or unbounded queries | read queries | list endpoints are paginated or bounded |

## D. Security & auth

| # | Gate | Command | Pass condition |
|---|---|---|---|
| D1 | No hardcoded secrets | `rg -n "(password\|secret\|api_key\|token)\s*=\s*['\"]" --glob '!*.example' --glob '!*.lock'` | zero real secrets; examples use placeholders |
| D2 | Secrets from env/config | read config module | no default fallback for production secrets |
| D3 | Auth on mutations | live requests | every mutating endpoint rejects unauthenticated calls (if spec declares auth) |
| D4 | Auth deps actually wired | read router deps | `Depends(...)` present, not just documented |
| D5 | Input validated | read schemas | Pydantic validation on every request body/param |
| D6 | No injection surface | read raw SQL | parameterised queries only |

## E. Configuration & environment

| # | Gate | Command | Pass condition |
|---|---|---|---|
| E1 | Config externalized | read config | all tunables from env, no magic constants |
| E2 | `.env.example` present | `test -f .env.example` | exists, lists every required var |
| E3 | No `.env` committed | `git ls-files .env` | not tracked |
| E4 | Runs from clean checkout | fresh venv + `pip install -r requirements.txt` | imports and starts |

## F. Delivery

| # | Gate | Command | Pass condition |
|---|---|---|---|
| F1 | Requirements pinned | read requirements.txt | deps listed with versions or constraints |
| F2 | App boots | `uvicorn src.main:app &` then `curl /health` | 200, correct body |
| F3 | Container build | `docker build -t probe .` | image builds |
| F4 | Container runs | `docker run -p 8000:8000 probe` then curl | 200, correct body |
| F5 | CI config present | `test -f .github/workflows/*.yml` | workflow runs lint + typecheck + test |
| F6 | README runnable | read README | a stranger can clone → install → run → test in ≤5 commands |
| F7 | Health endpoint | curl | exists, returns status |

## G. Process hygiene

| # | Gate | Command | Pass condition |
|---|---|---|---|
| G1 | No dead code / no stubs | `rg -n "TODO\|FIXME\|NotImplementedError\|pass  # stub"` | zero in shipped paths |
| G2 | No files outside intent | `git status` | only expected artifacts |
| G3 | Spec/plan lineage intact | `.githeri/specs/*.v*.yaml` | versioned specs present, `supersedes` chain unbroken |

## Scoring

- Gates passed / gates applicable = the score. Report the fraction, not a vibe.
- The headline number is **Githeri-verdict vs rubric-verdict**: if Githeri reports done while the
  rubric is below 100%, that gap is the finding, quantified.
