import os
import sys

root = "/Users/nickrotich/Desktop/portfolio/projects/python/test-githeri"
sys.path.insert(0, root)
for line in open(os.path.join(root, ".env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); os.environ[k] = v

spec_prompt = os.path.join(root, "evaluation", "prompts", "system_prompt_specgen.local.txt")
plan_prompt = os.path.join(root, "evaluation", "prompts", "plan_system_prompt.local.txt")
import githeri.core.spec_engine as se

se.load_system_prompt = lambda: open(spec_prompt, encoding="utf-8").read()
se.PLAN_SYSTEM_PROMPT = open(plan_prompt, encoding="utf-8").read()

import githeri.mcp.server as srv

work = os.path.join(root, "evaluation", "runs", "fresh_mcp")
prompt = open(os.path.join(root, "evaluation", "fixtures", "prompts", "full_template.md")).read()

synth = srv.synthesize_contract(feature_prompt=prompt, context_dir=work, provider="gemini", model="gemini-flash-lite-latest", use_local=True)
print("MCP SYNTH ok:", synth.get("ok"), "validated:", synth.get("validated"), "attempt:", synth.get("attempt"))
spec_slug = synth.get("spec_slug")
print("spec_slug:", spec_slug)

plan = srv.generate_plan(spec_slug_or_yaml=spec_slug, context_dir=work, provider="gemini", model="gemini-flash-lite-latest", use_local=True)
print("MCP PLAN keys:", list(plan.keys()))
print("MCP PLAN bytes:", len(plan.get("plan_md", "")))