import argparse, json, os, sys, shutil, subprocess, time
from pathlib import Path

root = "/Users/nickrotich/Desktop/portfolio/projects/python/test-githeri"
sys.path.insert(0, root)
for line in open(os.path.join(root, ".env")):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1); os.environ[k] = v
# Map NVIDIA key to OpenAI-compatible env vars for chatgpt provider
if os.environ.get("NVIDIA_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["NVIDIA_API_KEY"]
    os.environ.setdefault("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")

parser = argparse.ArgumentParser()
parser.add_argument("--prompts-dir", default=os.path.join(root, "evaluation", "fixtures", "prompts"))
parser.add_argument("--pattern", default="case_*.md")
parser.add_argument("--cloud", action="store_true")
parser.add_argument("--provider", default="gemini")
parser.add_argument("--model", default="gemini-flash-lite-latest")
parser.add_argument("--timeout", type=int, default=180)
args = parser.parse_args()

# Route chatgpt provider to the correct backend based on model name
if args.provider == "chatgpt":
    if "nvidia" in args.model.lower():
        os.environ["OPENAI_API_KEY"] = os.environ["NVIDIA_API_KEY"]
        os.environ["OPENAI_BASE_URL"] = "https://integrate.api.nvidia.com/v1"
    elif "reflection" in args.model.lower() or "beam" in args.model.lower():
        os.environ["OPENAI_API_KEY"] = os.environ["NOUSRESEARCH_API_KEY"]
        os.environ["OPENAI_BASE_URL"] = "https://inference-api.nousresearch.com/v1"

import githeri.core.spec_engine as se
if not args.cloud:
    spec_prompt = os.path.join(root, "evaluation", "prompts", "system_prompt_specgen.local.txt")
    plan_prompt = os.path.join(root, "evaluation", "prompts", "plan_system_prompt.local.txt")
    se.load_system_prompt = lambda: open(spec_prompt, encoding="utf-8").read()
    se.PLAN_SYSTEM_PROMPT = open(plan_prompt, encoding="utf-8").read()

githeri_bin = os.path.join(root, ".venv", "bin", "githeri")
cases_dir = Path(args.prompts_dir)
batch_root = Path(root) / "evaluation" / "runs" / ("batch_cloud" if args.cloud else "batch")
batch_root.mkdir(parents=True, exist_ok=True)

results = []
for case_file in sorted(cases_dir.glob(args.pattern)):
    case = case_file.stem
    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] START {case}", flush=True)
    work = batch_root / case
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / ".githeri").mkdir()
    (work / ".githeri" / "project.yaml").write_text(f"name: {case}\n")

    prompt = case_file.read_text()
    print(f"\n=== {case} ===", flush=True)
    try:
        res = se.generate_spec_local_or_remote(prompt=prompt, provider=args.provider, model=args.model, local=not args.cloud, timeout=args.timeout)
        spec_yaml = res.get("spec_yaml", "")
        spec_path = work / ".githeri" / "specs" / f"{case}.spec.yaml"
        spec_path.parent.mkdir(parents=True, exist_ok=True); spec_path.write_text(spec_yaml)

        plan_res = se.generate_plan_local_or_remote(prompt=prompt, spec_yaml=spec_yaml, provider=args.provider, model=args.model, local=not args.cloud, timeout=args.timeout)
        plan_md = plan_res.get("plan_md", "")
        plan_path = work / ".githeri" / "plans" / f"{case}.plan.md"
        plan_path.parent.mkdir(parents=True, exist_ok=True); plan_path.write_text(plan_md)

        out = subprocess.run([githeri_bin, "verify-exec", "--spec", str(spec_path), "--plan", str(plan_path), "--code", str(work), "--json"], capture_output=True, text=True, cwd=str(work))
        try: data = json.loads(out.stdout)
        except Exception: data = {"status": "error", "score": 0, "layers": []}

        import yaml as _yaml
        try:
            spec_obj = _yaml.safe_load(spec_yaml)
            ep_count = len(spec_obj.get("endpoints", [])) if isinstance(spec_obj, dict) else 0
        except Exception: ep_count = 0

        layer_status = {l["name"]: l["status"] for l in data.get("layers", [])}
        result = {"case": case, "spec_validated": res.get("validated"), "spec_attempt": res.get("attempt"), "endpoints": ep_count, "verify_status": data.get("status"), "score": data.get("score"), "layers": layer_status, "plan_bytes": len(plan_md)}
        print(json.dumps(result, indent=2))
        print(f"[{time.strftime('%H:%M:%S')}] DONE {case} score={result.get('score')} elapsed={round(time.time()-t0,1)}s", flush=True)
        results.append(result)
    except Exception as e:
        print("ERROR:", e)
        print(f"[{time.strftime('%H:%M:%S')}] FAIL {case} elapsed={round(time.time()-t0,1)}s", flush=True)
        results.append({"case": case, "error": str(e)})

summary_path = batch_root / "consistency_summary.json"
summary_path.write_text(json.dumps(results, indent=2))
print("\nWrote", summary_path)
