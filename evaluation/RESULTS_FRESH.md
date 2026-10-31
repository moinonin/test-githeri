# Githeri MCP + CLI Evaluation (fresh run, local Ollama only)

Model: qwen3.5:0.8b-mlx (CLI plan), qwen2.5-coder:0.5b (MCP synth in-process)
Ollama: http://127.0.0.1:11434
Githeri: 0.4.37
Prompt: evaluation/fixtures/prompts/full_template.md

## CLI
- `githeri init` -> OK
- `githeri plan --local --provider ollama --model qwen3.5:0.8b-mlx -f <prompt>` -> OK
  - Spec: .githeri/specs/software_request__1__objective.spec.yaml
  - Plan: .githeri/plans/software_request__1__objective.plan.md
- `githeri verify` -> All 0 expected endpoints verified (no code yet); boot check: unknown (no entrypoint)
- `githeri verify-exec` -> Status: fail | Static score: 0.20
  - path_integrity: FAIL (src/tasks.py absent; tests path absent)
  - embedded_python_static: FAIL (sqlalchemy not found in env)
  - plan_structure: PASS

## MCP (in-process, production mode, no bypass)
- synthesize_contract (qwen2.5-coder:0.5b, use_local=True, use_cloud=False):
  - validated=False after 3 retries (~119s)
  - Spec produced but failed schema validation
- Cloud quota reservation (reserve_usage engine=local): OK, 1.7s

## Notes
- MCP transport adds overhead; in-process result is representative of MCP outcome.
- Local 0.5b model emits spec but fails validation after retries (consistent with prior finding: small models don't emit endpoint-rich/valid specs; recommend 7b+).
- No IP leaks: all generation local; cloud only used for quota reservation (allowed entitlement).
