# Githeri MCP — Totality Evaluation Plan

Purpose: evaluate whether the Githeri MCP surface can carry a feature from natural-language
intake to production-grade software, and identify exactly where it fails.

Scope boundary: this directory is an evaluation sandbox. It is not the product.

## Baseline facts (verified 2026-10-25, githeri 0.4.33)

| Fact | Value | Consequence |
|---|---|---|
| Version | 0.4.33 (PyPI, `githeri[mcp]`) | current |
| MCP transport | stdio, `githeri mcp`, 21 tools | connected, 938–1049 ms |
| Auth | `~/.githeri/credentials.json` — tier `solo`, git_live key | present |
| Cloud synthesis (`use_cloud=true`) | **FAILS 503** — bundled engine (llama-server :8080) not ready | never use the default path |
| Local synthesis (`use_cloud=false`, `provider=gemini`) | works, spec validated on attempt 1 | pin `provider` + `use_cloud=false` on every LLM call |
| MCP exec/run tool | **absent** | execution is CLI-only → two paths must be compared |
| Repo state at start | 8 specs (6 stale `baseline_*` from a deleted `app/`), 3 plans, 1 stale run, git with zero commits | drift measurement starts at 0/14 — must reset before measuring |

## Harness layout

```
evaluation/
  PLAN.md              # this file
  RESULTS.md           # measured log — one section per phase, no prose-only claims
  rubric.md            # production-grade gate definitions (hard criteria, pass/fail)
  fixtures/prompts/    # S1 intake fixtures: vague / medium / full 9-section
  fixtures/seed_app/   # reference FastAPI app for S5 brownfield round-trip
  scenarios/           # per-phase prompt + expectation files
  runs/<phase>/<sc>/   # isolated per-scenario workspaces (fresh .githeri/ each)
  legacy/              # archived pre-existing state (moved, not deleted)
tools/
  collect.sh           # pulls githeri state + test results into RESULTS.md
```

Every scenario runs in its own copy under `evaluation/runs/` with a fresh `.githeri/`.
No scenario mutates the repo-root `.githeri/`.

## Phases and gates

### Phase 0 — Harness + reset  [gate: measurements start from a clean, known state]
- Archive existing `.githeri/specs`, `.githeri/plans`, `.githeri/runs` → `evaluation/legacy/`.
- Make an initial commit so `approve_spec` provenance has a commit to point at.
- Record the 21-tool inventory + provider config as the baseline manifest.

### Phase 1 — Intake depth  [gate: does intake elicit what a competent engineer would ask?]
Three fixtures, same session flow: `intake_start` → `intake_next_question` → `intake_answer` → … →
`intake_validate` → `intake_preview` → `intake_confirm` → `intake_compile` → `intake_submit`.

| Metric | Where measured |
|---|---|
| readiness_score before/after answering | intake_start, intake_validate |
| CLEAR-SPEC dimension coverage (10 dims) | intake_start payload |
| coaching findings count + severity | intake_start payload |
| questions asked, material vs. default-tier | next_question loop |
| compile blocked without force? | intake_compile |
| submitted spec validates + lands in specs dir | intake_submit |

Expected: vague fixture → question count up, readiness lifts materially; full-template fixture →
near-zero questions. A no-lift case is a finding.

### Phase 2 — Spec → Plan  [gate: is the plan executable without reinterpretation?]
- `synthesize_contract` on the Phase-1 output, `provider=gemini`, `use_cloud=false`.
- `generate_plan` on the resulting spec.
- `verify_executability(spec_yaml, plan_md)` — static readiness.
Metrics: plan stage count, per-stage verification commands present, commands actually runnable
in the scenario workspace (executed, not assumed), executability verdict, blueprint-vs-plan
semantic agreement (read both, compare intent).

### Phase 3 — Execution, MCP-native  [gate: can the contract engine's output drive a coding agent to green?]
Hermes acts as the coding agent, consuming only MCP artifacts (spec + plan) plus its own file tools.
Loop: implement stage → `githeri_patch_router` → `githeri_verify_drift` → fix.
Metrics: drift closure (expected → implemented), lint clean, typecheck clean, pytest pass,
self-heal iterations, tokens/time.

### Phase 4 — Execution, CLI-native  [gate: is the native headless executor better than the agent path?]
Same plan, `githeri exec <plan> --code <workspace> --isolated --provider gemini`.
Metrics: same as Phase 3, plus: escalation to AGENT_RESCUE handoff, files written, sandbox usage,
then `githeri diff`/`runs` ledger completeness.

Phases 3 and 4 are the comparison that decides whether the MCP surface alone is a sufficient
production path. Both must reach the same rubric, or the rubric is what is wrong.

### Phase 5 — Brownfield round-trip  [gate: can it re-derive a contract from code it produced?]
- `baseline_from_code` on the Phase-3/4 output app.
- Compare generated baseline specs against the authored spec: endpoint set match, auth coverage,
  negative cases captured. This measures whether the contract is recoverable from the artifact.

### Phase 6 — Continuity + enforcement  [gate: does the contract stay enforced across change?]
- `update_spec` (spec mutation) → `continue_feature` (version bump, lineage) → `next_stage`.
- `githeri verify` / `check-pr` / `hook install` → commit → confirm the gate actually fails a
  deliberately drifted commit.
- `audit_report` on the final tree.

### Phase 7 — Production-grade bar  [gate: the hard question]
Githeri verifies *contract coverage*, not *code quality*. This phase scores the final artifact
against `rubric.md` independently of Githeri's own verdict: typing, lint, test depth, error
handling, auth, config externalization, secrets hygiene, migrations, containerization, CI, docs.
The headline finding will be the gap between "Githeri says done" and "production-grade says done".

## Metric discipline

- Every number in RESULTS.md comes from a tool output in that phase's run directory.
- Failures are classified: GITHERI-DEFECT / CLOUD-ENTITLEMENT / LLM-QUALITY / HARNESS.
- A phase is not "pass" because a tool returned ok:true — it passes when its rubric gates pass.
- Prior numbers that do not reproduce are reported as prior numbers, not quietly restated.

## Explicit non-goals

- Not a benchmark of Gemini vs other providers (one provider, pinned, held constant).
- Not a fix-fest: defects found are recorded with reproduction, not patched in the product repo
  during evaluation.
