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

work = os.path.join(root, "evaluation", "runs", "fresh_cli")
prompt = open(os.path.join(root, "evaluation", "fixtures", "prompts", "full_template.md")).read()

res = se.generate_spec_local_or_remote(prompt=prompt, provider="gemini", model="gemini-flash-lite-latest", local=True, timeout=120)
print("CLI SPEC validated:", res.get("validated"), "attempt:", res.get("attempt"))
spec_yaml = res.get("spec_yaml", "")
os.makedirs(os.path.join(work, ".githeri", "specs"), exist_ok=True)
open(os.path.join(work, ".githeri", "specs", "fresh_cli.spec.yaml"), "w").write(spec_yaml)

plan_res = se.generate_plan_local_or_remote(prompt=prompt, spec_yaml=spec_yaml, provider="gemini", model="gemini-flash-lite-latest", local=True, timeout=120)
plan_md = plan_res.get("plan_md", "")
os.makedirs(os.path.join(work, ".githeri", "plans"), exist_ok=True)
open(os.path.join(work, ".githeri", "plans", "fresh_cli.plan.md"), "w").write(plan_md)
print("CLI PLAN bytes:", len(plan_md))