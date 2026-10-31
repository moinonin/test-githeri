import json, os, sys, shutil, subprocess, time
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

import githeri.core.spec_engine as se

# Reasoning-content fallback for _call_chatgpt (handles reasoning-only models)
_original_chatgpt = se._call_chatgpt
def _chatgpt_with_fallback(system_prompt, user_prompt, model=None, timeout=180):
    import requests
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = os.environ.get("OPENAI_API_KEY")
    payload = {
        "model": model or "gpt-4o",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    r = requests.post(f"{base_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, timeout=timeout)
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    content = msg.get("content")
    if not content:
        content = msg.get("reasoning_content")
    return content
se._call_chatgpt = _chatgpt_with_fallback

spec_prompt_path = Path(root) / "evaluation" / "prompts" / "system_prompt_specgen.local.txt"
plan_prompt_path = Path(root) / "evaluation" / "prompts" / "plan_system_prompt.local.txt"
se.load_system_prompt = lambda: spec_prompt_path.read_text()
se.PLAN_SYSTEM_PROMPT = plan_prompt_path.read_text()

githeri_bin = os.path.join(root, ".venv", "bin", "githeri")
cases_dir = Path(root) / "evaluation" / "fixtures" / "prompts"
batch_root = Path(root) / "evaluation" / "runs" / "self_improve"
batch_root.mkdir(parents=True, exist_ok=True)

def run_batch(case_names, prompt_dir, provider="gemini", model="gemini-flash-lite-latest", timeout=120):
    results = []
    for name in case_names:
        case_file = Path(prompt_dir) / f"{name}.md"
        t0 = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] START {name}", flush=True)
        work = batch_root / name
        if work.exists(): shutil.rmtree(work)
        work.mkdir(parents=True)
        (work / ".githeri").mkdir()
        (work / ".githeri" / "project.yaml").write_text(f"name: {name}\n")
        prompt = case_file.read_text()
        try:
            res = se.generate_spec_local_or_remote(prompt=prompt, provider=provider, model=model, local=True, timeout=timeout)
            spec_yaml = res.get("spec_yaml", "")
            sp = work / ".githeri" / "specs" / f"{name}.spec.yaml"
            sp.parent.mkdir(parents=True, exist_ok=True); sp.write_text(spec_yaml)
            plan_res = se.generate_plan_local_or_remote(prompt=prompt, spec_yaml=spec_yaml, provider=provider, model=model, local=True, timeout=timeout)
            plan_md = plan_res.get("plan_md", "")
            pp = work / ".githeri" / "plans" / f"{name}.plan.md"
            pp.parent.mkdir(parents=True, exist_ok=True); pp.write_text(plan_md)
            out = subprocess.run([githeri_bin, "verify-exec", "--spec", str(sp), "--plan", str(pp), "--code", str(work), "--json"], capture_output=True, text=True, cwd=str(work))
            data = json.loads(out.stdout)
            layers = {l["name"]: l["status"] for l in data.get("layers", [])}
            core = sum(1 for k in ("spec_validation","plan_structure","path_integrity","command_syntax_and_safety") if layers.get(k) == "pass")
            custom_score = core / 4.0
            results.append({"case": name, "score": data.get("score", 0), "custom_score": custom_score, "layers": layers})
            print(f"[{time.strftime('%H:%M:%S')}] DONE {name} score={data.get('score',0)} custom={custom_score} elapsed={round(time.time()-t0,1)}s", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] FAIL {name} elapsed={round(time.time()-t0,1)}s error={str(e)[:80]}", flush=True)
            results.append({"case": name, "score": 0, "error": str(e)})
    avg = sum(r.get("custom_score", r.get("score", 0)) for r in results) / len(results) if results else 0
    failures = [r for r in results if r.get("custom_score", r.get("score",0)) < 1.0]
    return avg, results, failures

def valid_prompt(candidate):
    required = ["### Stage 1", "### Stage 2", "### Stage 3", "### Stage 4", "Output clean Markdown", "column 0"]
    if any(r not in candidate for r in required):
        return False
    if '"parts"' in candidate or "JSON object" in candidate:
        return False
    return True

def propose_revision(current_prompt, failures, provider="gemini", model="gemini-flash-lite-latest", timeout=120):
    meta_system = ("You are a prompt engineer. Revise the given plan-generation system prompt to fix the listed failures. "
                   "Preserve the required stage headings and column-0 code rule. Output ONLY the full revised prompt text in clean Markdown, no markdown fences, no JSON. "
                   "Do not change the output format; do not request JSON or 'parts' keys.")
    failure_text = json.dumps(failures, indent=2)
    user = f"CURRENT PROMPT:\n{current_prompt}\n\nFAILURES:\n{failure_text}\n\nReturn the full revised prompt."
    if provider == "chatgpt":
        return se._call_chatgpt(meta_system, user, model=model, timeout=timeout)
    return se._call_gemini(meta_system, user, model=model)

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts-dir", default=str(cases_dir))
    parser.add_argument("--pattern", default="case_*.md")
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-flash-lite-latest")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    provider = args.provider
    model = args.model
    timeout = args.timeout
    # Route chatgpt provider to the correct backend based on model name
    if provider == "chatgpt":
        if "nvidia" in model.lower():
            os.environ["OPENAI_API_KEY"] = os.environ["NVIDIA_API_KEY"]
            os.environ["OPENAI_BASE_URL"] = "https://integrate.api.nvidia.com/v1"
        elif "reflection" in model.lower() or "beam" in model.lower():
            os.environ["OPENAI_API_KEY"] = os.environ["NOUSRESEARCH_API_KEY"]
            os.environ["OPENAI_BASE_URL"] = "https://inference-api.nousresearch.com/v1"
    prompt_dir = Path(args.prompts_dir)
    case_names = [p.stem for p in sorted(prompt_dir.glob(args.pattern))]
    if not case_names:
        print("No prompts found."); return
    # run_batch expects case names; but run_batch builds paths from cases_dir global.
    # To support arbitrary dir, temporarily override cases_dir by monkey? Instead, copy prompt files? 
    # Simpler: run_batch uses global cases_dir; set it.
    cases = case_names
    print("Baseline run...")
    base_avg, base_res, base_fail = run_batch(cases, prompt_dir, provider=provider, model=model, timeout=timeout)
    print(f"Baseline avg score: {base_avg}")
    print(json.dumps(base_fail, indent=2))

    current = plan_prompt_path.read_text()
    print("Proposing revision...")
    candidate = propose_revision(current, base_fail, provider=provider, model=model, timeout=timeout)
    if not valid_prompt(candidate):
        print("Candidate invalid (format). Reverting without evaluation.")
        plan_prompt_path.write_text(current)
        se.PLAN_SYSTEM_PROMPT = current
        # write summary
        summary = {"baseline_avg": base_avg, "candidate_avg": base_avg, "kept": False, "reason": "invalid_prompt", "baseline": base_res, "candidate": []}
        (batch_root / "self_improve_summary.json").write_text(json.dumps(summary, indent=2))
        return
    backup = current
    plan_prompt_path.write_text(candidate)
    se.PLAN_SYSTEM_PROMPT = candidate

    print("Candidate run...")
    cand_avg, cand_res, cand_fail = run_batch(cases, prompt_dir, provider=provider, model=model, timeout=timeout)
    print(f"Candidate avg score: {cand_avg}")

    base_path_pass = sum(1 for r in base_res if r.get("layers", {}).get("path_integrity") == "pass")
    cand_path_pass = sum(1 for r in cand_res if r.get("layers", {}).get("path_integrity") == "pass")

    if cand_avg > base_avg and cand_path_pass >= base_path_pass:
        print("KEEP candidate (improved).")
        kept = True
    else:
        print("REVERT candidate (no improvement).")
        plan_prompt_path.write_text(backup)
        se.PLAN_SYSTEM_PROMPT = backup
        kept = False

    summary = {"baseline_avg": base_avg, "candidate_avg": cand_avg, "kept": kept, "baseline": base_res, "candidate": cand_res}
    (batch_root / "self_improve_summary.json").write_text(json.dumps(summary, indent=2))
    print("Wrote summary.")

if __name__ == "__main__":
    main()
