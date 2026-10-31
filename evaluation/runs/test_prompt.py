import os, sys
root = "/Users/nickrotich/Desktop/portfolio/projects/python/test-githeri"
sys.path.insert(0, root)
for line in open(os.path.join(root, ".env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); os.environ[k] = v

prompt_path = os.path.join(root, "evaluation", "prompts", "system_prompt_specgen.local.txt")
import githeri.core.spec_engine as se
se.load_system_prompt = lambda: open(prompt_path, encoding="utf-8").read()

prompt = open(os.path.join(root, "evaluation", "fixtures", "prompts", "full_template.md")).read()
res = se.generate_spec_local_or_remote(
    prompt=prompt, provider="gemini", model="gemini-flash-lite-latest", local=True, timeout=120
)
print("validated:", res.get("validated"), "attempt:", res.get("attempt"))
print("errors:", res.get("validation_errors"))
yaml_text = res.get("spec_yaml", "")
open(os.path.join(root, "evaluation", "runs", "prompt_test.spec.yaml"), "w").write(yaml_text)
print(yaml_text)