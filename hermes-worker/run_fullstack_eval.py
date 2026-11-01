#!/usr/bin/env python3
"""Full-Stack Multi-App Evaluation Harness.

Benchmarks prompt-to-contract-to-code execution across full-stack applications.
Supports Dry-Run verification (M1-M5) and Live Autonomous Agent execution (M1-M18).
Runs under test-githeri/hermes-worker (or any designated agent worker workspace).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml
from rich.console import Console
from rich.table import Table

console = Console()


def load_env_file(env_path: Path) -> None:
    """Loads key-value pairs from .env into os.environ."""
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


def resolve_githeri_bin(worker_dir: Path) -> str:
    """Resolves githeri CLI executable."""
    for cand in (
        worker_dir.resolve() / ".venv" / "bin" / "githeri",
        worker_dir.resolve().parent / ".venv" / "bin" / "githeri",
    ):
        if cand.is_file():
            return str(cand)
    sys_cand = shutil.which("githeri")
    if sys_cand:
        return sys_cand
    raise RuntimeError(f"Cannot locate githeri executable in {worker_dir} or PATH.")


def resolve_pytest_bin(worker_dir: Path) -> str:
    """Resolves pytest executable."""
    for cand in (
        worker_dir.resolve() / ".venv" / "bin" / "pytest",
        worker_dir.resolve().parent / ".venv" / "bin" / "pytest",
    ):
        if cand.is_file():
            return str(cand)
    sys_cand = shutil.which("pytest")
    if sys_cand:
        return sys_cand
    return "pytest"


def resolve_ruff_bin(worker_dir: Path) -> str:
    """Resolves ruff executable."""
    for cand in (
        worker_dir.resolve() / ".venv" / "bin" / "ruff",
        worker_dir.resolve().parent / ".venv" / "bin" / "ruff",
    ):
        if cand.is_file():
            return str(cand)
    sys_cand = shutil.which("ruff")
    if sys_cand:
        return sys_cand
    return "ruff"


def evaluate_dry_run_case(case_dir: Path, case_name: str, duration: float) -> Dict[str, Any]:
    """Evaluates Metrics M1 through M5 for a dry-run workspace."""
    metrics: Dict[str, Any] = {
        "case": case_name,
        "m1_spec_valid": False,
        "m2_endpoints_count": 0,
        "m3_sdk_methods_count": 0,
        "m4_ui_plan_stage0": False,
        "m5_scaffold_build": False,
        "duration_seconds": round(duration, 2),
        "errors": [],
    }

    # M1 & M2: Spec validation & endpoints count
    specs_dir = case_dir / ".githeri" / "specs"
    spec_files = list(specs_dir.glob("*.spec.yaml")) if specs_dir.is_dir() else []
    if not spec_files:
        metrics["errors"].append("No .spec.yaml generated in .githeri/specs")
    else:
        spec_file = spec_files[0]
        try:
            content = spec_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if isinstance(data, dict) and ("endpoints" in data or "local_goals" in data or "business_rules" in data):
                metrics["m1_spec_valid"] = True
                metrics["m2_endpoints_count"] = len(data.get("endpoints", []))
            else:
                metrics["errors"].append("Spec YAML missing 'endpoints' or 'local_goals' block")
        except Exception as e:
            metrics["errors"].append(f"Spec YAML parse error: {e}")

    # M3: TypeScript SDK client inspection
    client_ts = case_dir / "frontend" / "src" / "api" / "client.ts"
    if client_ts.is_file():
        code = client_ts.read_text(encoding="utf-8")
        methods = re.findall(r"(?:async\s+)?([a-zA-Z0-9_]+)\s*\([^)]*\)\s*:\s*Promise", code)
        metrics["m3_sdk_methods_count"] = len(methods)
    else:
        metrics["errors"].append("frontend/src/api/client.ts missing")

    # M4: UI Plan Runway inspection (Stage 0 presence)
    plans_dir = case_dir / ".githeri" / "plans"
    ui_plan_files = list(plans_dir.glob("*.ui.plan.md")) if plans_dir.is_dir() else []
    if ui_plan_files:
        ui_plan_text = ui_plan_files[0].read_text(encoding="utf-8")
        if "Stage 0" in ui_plan_text and ("CORSMiddleware" in ui_plan_text or "StaticFiles" in ui_plan_text):
            metrics["m4_ui_plan_stage0"] = True
        else:
            metrics["errors"].append("UI plan missing Stage 0 CORS / StaticFiles integration")
    else:
        metrics["errors"].append("No .ui.plan.md generated in .githeri/plans")

    # M5: Scaffold Vite Build test
    frontend_dir = case_dir / "frontend"
    if frontend_dir.is_dir() and (frontend_dir / "package.json").is_file():
        build_res = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if build_res.returncode == 0:
            metrics["m5_scaffold_build"] = True
        else:
            metrics["errors"].append(f"npm run build failed (exit {build_res.returncode}): {build_res.stderr[-300:]}")
    else:
        metrics["errors"].append("frontend directory or package.json missing")

    metrics["all_passed"] = (
        metrics["m1_spec_valid"]
        and metrics["m2_endpoints_count"] > 0
        and metrics["m3_sdk_methods_count"] > 0
        and metrics["m4_ui_plan_stage0"]
        and metrics["m5_scaffold_build"]
    )
    return metrics


def evaluate_live_case(
    case_dir: Path,
    case_name: str,
    duration: float,
    worker_dir: Path,
    githeri_bin: str,
) -> Dict[str, Any]:
    """Evaluates Metrics M1 through M18 for a completed live agent execution."""
    dry_metrics = evaluate_dry_run_case(case_dir, case_name, duration)
    metrics: Dict[str, Any] = {
        **dry_metrics,
        "m6_contract_parity": False,
        "m7_tests_pass": False,
        "m8_dynamic_logic": False,
        "m9_static_hygiene": False,
        "m10_frontend_build_clean": False,
        "m11_live_api_binding": False,
        "m12_triple_state_handling": False,
        "m13_domain_adaptation": False,
        "m14_zero_hardcoded_localhost": False,
        "live_passed": False,
    }

    pytest_bin = resolve_pytest_bin(worker_dir)
    ruff_bin = resolve_ruff_bin(worker_dir)

    # M6: Contract parity via githeri verify
    try:
        verify_proc = subprocess.run(
            [githeri_bin, "verify"],
            cwd=str(case_dir),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if verify_proc.returncode == 0 and "missing" not in verify_proc.stdout.lower():
            metrics["m6_contract_parity"] = True
        else:
            metrics["errors"].append("githeri verify failed or reported drift")
    except Exception as e:
        metrics["errors"].append(f"githeri verify exception: {e}")

    # M7: Automated tests pass via pytest
    try:
        py_env = dict(os.environ)
        paths = [str(case_dir.resolve())]
        if (case_dir / "backend").is_dir():
            paths.append(str((case_dir / "backend").resolve()))
        if (case_dir / "src").is_dir():
            paths.append(str((case_dir / "src").resolve()))
        py_env["PYTHONPATH"] = os.pathsep.join(paths) + (os.pathsep + py_env.get("PYTHONPATH", "") if py_env.get("PYTHONPATH") else "")
        pytest_cmd = [pytest_bin, "-q", "tests/"] if (case_dir / "tests").is_dir() else [pytest_bin, "-q"]
        pytest_proc = subprocess.run(
            pytest_cmd,
            cwd=str(case_dir),
            capture_output=True,
            text=True,
            timeout=90,
            env=py_env,
        )
        if pytest_proc.returncode == 0:
            metrics["m7_tests_pass"] = True
        else:
            metrics["errors"].append(f"pytest failed: {pytest_proc.stderr[-300:] or pytest_proc.stdout[-300:]}")
    except Exception as e:
        metrics["errors"].append(f"pytest exception: {e}")

    # M8: Dynamic business logic (asserts present in tests)
    test_files = list((case_dir / "tests").rglob("test_*.py")) if (case_dir / "tests").is_dir() else []
    if test_files:
        test_content = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in test_files)
        # Check that tests assert real output or status transitions, not dummy stubs
        if "assert " in test_content and len(re.findall(r"assert\s+", test_content)) >= 3:
            metrics["m8_dynamic_logic"] = True
        else:
            metrics["errors"].append("Tests lack sufficient dynamic assertions")
    else:
        metrics["errors"].append("No test files found in tests/")

    # M9: Static code hygiene (Ruff & passlib check)
    try:
        candidate_dirs = [
            d.name for d in case_dir.iterdir()
            if d.is_dir() and d.name in ("src", "app", "orders", "config", "tests") and not d.name.startswith(".")
        ]
        target_dirs = candidate_dirs if candidate_dirs else ["."]
        ruff_proc = subprocess.run(
            [ruff_bin, "check", *target_dirs, "--select", "F821,E9"],
            cwd=str(case_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        py_files = [
            f for f in case_dir.rglob("*.py")
            if not any(p in f.parts for p in (".venv", "node_modules", "tests", ".pytest_cache", ".ruff_cache"))
        ]
        src_content = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in py_files)
        has_passlib = "passlib" in src_content
        if ruff_proc.returncode == 0 and not has_passlib:
            metrics["m9_static_hygiene"] = True
        else:
            if has_passlib:
                metrics["errors"].append("Deprecated passlib detected in src/")
            if ruff_proc.returncode != 0:
                metrics["errors"].append(f"Ruff syntax/undefined var errors: {ruff_proc.stdout[-300:]}")
    except Exception as e:
        metrics["errors"].append(f"Ruff check exception: {e}")

    # M10: Production bundle build
    frontend_dir = case_dir / "frontend"
    if frontend_dir.is_dir() and (frontend_dir / "package.json").is_file():
        build_proc = subprocess.run(
            ["npm", "run", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if build_proc.returncode == 0:
            metrics["m10_frontend_build_clean"] = True
        else:
            metrics["errors"].append("Frontend npm run build failed after agent execution")

    # M11 - M14: Frontend quality & hygiene inspection
    ui_files = list((frontend_dir / "src").glob("**/*.tsx")) if (frontend_dir / "src").is_dir() else []
    ui_content = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in ui_files)

    # M11: Live API client binding (no mock data arrays)
    has_api_call = bool(
        re.search(r"['\"].*api/client['\"]", ui_content)
        or "api." in ui_content
        or "(api as any)" in ui_content
        or "apiClient" in ui_content
        or "fetch(" in ui_content
        or "axios." in ui_content
    )
    has_mock_array = bool(re.search(r"const\s+MOCK_\w+\s*=", ui_content))
    if has_api_call and not has_mock_array:
        metrics["m11_live_api_binding"] = True
    else:
        if not has_api_call:
            metrics["errors"].append("UI does not invoke api client or backend endpoints")
        if has_mock_array:
            metrics["errors"].append("Lingering mock data array (MOCK_...) found in UI")

    # M12: Triple state handling
    has_loading = "loading" in ui_content.lower() or "spinner" in ui_content.lower() or "skeleton" in ui_content.lower()
    has_empty = "empty" in ui_content.lower() or "no " in ui_content.lower()
    has_error = "error" in ui_content.lower()
    if has_loading and has_empty and has_error:
        metrics["m12_triple_state_handling"] = True
    else:
        metrics["errors"].append("UI missing one or more required states (loading/empty/error)")

    # M13: Domain adaptation (not generic Item)
    has_generic_item = "Item Management" in ui_content or "ItemList" in ui_content
    if not has_generic_item:
        metrics["m13_domain_adaptation"] = True
    else:
        metrics["errors"].append("UI still contains generic 'Item Management' scaffold")

    # M14: Zero hardcoded localhost:8000
    has_hardcoded_localhost = "localhost:8000" in ui_content or "127.0.0.1:8000" in ui_content
    if not has_hardcoded_localhost:
        metrics["m14_zero_hardcoded_localhost"] = True
    else:
        metrics["errors"].append("Hardcoded localhost:8000 URL found in UI code")

    metrics["live_passed"] = (
        metrics["m6_contract_parity"]
        and metrics["m7_tests_pass"]
        and metrics["m9_static_hygiene"]
        and metrics["m10_frontend_build_clean"]
        and metrics["m11_live_api_binding"]
        and metrics["m14_zero_hardcoded_localhost"]
    )
    return metrics


def run_fullstack_evaluation() -> None:
    parser = argparse.ArgumentParser(description="Githeri Full-Stack Evaluation Runner")
    parser.add_argument(
        "--prompts-dir",
        default=None,
        help="Path to directory containing prompt markdown files (case_*.md)",
    )
    parser.add_argument(
        "--pattern",
        default="case_*.md",
        help="File pattern for case prompts (default: case_*.md)",
    )
    parser.add_argument(
        "--cases",
        default=None,
        help="Comma-separated subset of case names (e.g. case_01,case_02)",
    )
    parser.add_argument(
        "--agent",
        default="hermes",
        help="Target autonomous agent driver (default: hermes)",
    )
    parser.add_argument(
        "--provider",
        default="chatgpt",
        help="Provider for contract & runway synthesis (default: chatgpt)",
    )
    parser.add_argument(
        "--model",
        default="reflection/beam-1.0-501b-a23b:free",
        help="Model name for contract synthesis (default: reflection/beam-1.0-501b-a23b:free)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run spec synthesis and scaffold build verification without spawning agent",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Launch live autonomous agent chat session to generate code",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        default=False,
        help="Re-evaluate existing runs in runs-dir without generating code or synthesizing",
    )
    parser.add_argument(
        "--runs-dir",
        default="runs",
        help="Directory to store evaluation runs (default: runs)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1200,
        help="Timeout in seconds per live agent case run (default: 1200)",
    )
    args = parser.parse_args()

    # Default to dry-run if neither --live nor --dry-run nor --eval-only explicitly specified
    if not args.live and not args.dry_run and not args.eval_only:
        args.dry_run = True

    worker_dir = Path.cwd().resolve()
    load_env_file(worker_dir / ".env")

    # Locate prompts directory
    prompts_dir = None
    if args.prompts_dir:
        prompts_dir = Path(args.prompts_dir).resolve()
    else:
        cand1 = worker_dir.parent / "evaluation" / "dev_prompts" / "normalized"
        cand2 = worker_dir.parent.parent / "ai" / "githeri" / "evaluation" / "fixtures" / "dev_prompts"
        if cand1.is_dir():
            prompts_dir = cand1
        elif cand2.is_dir():
            prompts_dir = cand2

    if not prompts_dir or not prompts_dir.is_dir():
        console.print(f"[bold red]Could not find prompts directory. Checked {args.prompts_dir}.[/bold red]")
        sys.exit(1)

    prompt_files = sorted(prompts_dir.glob(args.pattern))
    if args.cases:
        selected = {c.strip() for c in args.cases.split(",")}
        prompt_files = [f for f in prompt_files if f.stem in selected]

    if not prompt_files:
        console.print(f"[bold red]No matching prompt files found in {prompts_dir}[/bold red]")
        sys.exit(1)

    githeri_bin = resolve_githeri_bin(worker_dir)
    runs_dir = worker_dir / args.runs_dir
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Pre-warmed template node_modules in worker_dir / ".cache" / "frontend_template"
    cache_dir = worker_dir / ".cache" / "frontend_template"
    cached_node_modules = cache_dir / "node_modules"
    if not (cached_node_modules / ".bin" / "tsc").is_file():
        console.print("[dim]Pre-warming shared frontend node_modules cache...[/dim]")
        cache_dir.mkdir(parents=True, exist_ok=True)
        template_pkg = {
            "name": "template-cache",
            "private": True,
            "type": "module",
            "dependencies": {
                "react": "^18.3.1",
                "react-dom": "^18.3.1",
                "lucide-react": "^0.460.0",
            },
            "devDependencies": {
                "@tailwindcss/vite": "^4.0.0",
                "@types/react": "^18.3.12",
                "@types/react-dom": "^18.3.1",
                "@vitejs/plugin-react": "^4.3.4",
                "tailwindcss": "^4.0.0",
                "typescript": "~5.6.3",
                "vite": "^6.0.0",
            },
        }
        (cache_dir / "package.json").write_text(json.dumps(template_pkg, indent=2), encoding="utf-8")
        subprocess.run(["npm", "install"], cwd=str(cache_dir), capture_output=True, check=True)

    mode_label = "LIVE AGENT EXECUTION" if args.live else "DRY-RUN (Runway & Scaffold Verification)"
    console.print(
        f"[bold cyan]Starting Full-Stack Evaluation[/bold cyan]\n"
        f"• Prompts: [yellow]{prompts_dir}[/yellow] ({len(prompt_files)} cases)\n"
        f"• Worker: [yellow]{worker_dir}[/yellow]\n"
        f"• Mode: [bold green]{mode_label}[/bold green]\n"
        f"• Model: [cyan]{args.model}[/cyan] ({args.provider})\n"
        f"• Agent: [cyan]{args.agent}[/cyan]\n"
        f"• Binary: [cyan]{githeri_bin}[/cyan]\n"
    )

    results: List[Dict[str, Any]] = []

    for idx, prompt_file in enumerate(prompt_files, 1):
        case_name = prompt_file.stem
        case_dir = runs_dir / case_name

        if args.eval_only:
            if not case_dir.is_dir():
                console.print(f"[dim yellow]Skipping {case_name}: directory not found in {runs_dir}[/dim yellow]")
                continue
            console.print(f"\n[bold cyan]─── [{idx}/{len(prompt_files)}] Evaluating {case_name} ───[/bold cyan]")
            case_metrics = evaluate_live_case(case_dir, case_name, 0.0, worker_dir, githeri_bin)
            results.append(case_metrics)
            status_icon = "✔" if case_metrics.get("live_passed") else "✖"
            status_color = "green" if case_metrics.get("live_passed") else "red"
            console.print(
                f"[{status_color}]{status_icon} {case_name} EVAL completed | "
                f"Parity: {case_metrics['m6_contract_parity']} | "
                f"Tests: {case_metrics['m7_tests_pass']} | "
                f"Frontend Build: {case_metrics['m10_frontend_build_clean']}[/{status_color}]"
            )
            if case_metrics["errors"]:
                for err in case_metrics["errors"]:
                    console.print(f"  [dim red]! {err}[/dim red]")
            continue

        if case_dir.exists():
            shutil.rmtree(case_dir)
        case_dir.mkdir(parents=True)

        # Copy runtime configs (.env, AGENTS.md, .hermes)
        if (worker_dir / ".env").is_file():
            shutil.copy2(worker_dir / ".env", case_dir / ".env")
        if (worker_dir / "AGENTS.md").is_file():
            shutil.copy2(worker_dir / "AGENTS.md", case_dir / "AGENTS.md")
        if (worker_dir / ".hermes").is_dir():
            shutil.copytree(worker_dir / ".hermes", case_dir / ".hermes")

        prompt_text = prompt_file.read_text(encoding="utf-8").strip()
        console.print(f"\n[bold magenta]─── [{idx}/{len(prompt_files)}] Synthesizing {case_name} ───[/bold magenta]")

        t0 = time.time()
        start_cmd = [
            githeri_bin,
            "start",
            args.agent,
            prompt_text,
            "--fullstack",
            "--dry-run",
            "--local",
            "--provider",
            args.provider,
            "--model",
            args.model,
        ]

        # Execute runway synthesis
        proc = subprocess.run(
            start_cmd,
            cwd=str(case_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode != 0:
            duration = time.time() - t0
            console.print(f"[bold red]❌ Synthesis failed for {case_name}:[/bold red]\n{proc.stderr[-400:]}")
            results.append({
                "case": case_name,
                "all_passed": False,
                "error": proc.stderr[-400:],
                "duration_seconds": round(duration, 2),
            })
            continue

        # Symlink cached node_modules into case frontend workspace
        case_frontend = case_dir / "frontend"
        if case_frontend.is_dir() and cached_node_modules.is_dir():
            target_nm = case_frontend / "node_modules"
            if not target_nm.exists():
                target_nm.symlink_to(cached_node_modules.resolve())

        if not args.live:
            # DRY-RUN EVALUATION
            duration = time.time() - t0
            case_metrics = evaluate_dry_run_case(case_dir, case_name, duration)
            results.append(case_metrics)

            status_icon = "✔" if case_metrics["all_passed"] else "✖"
            status_color = "green" if case_metrics["all_passed"] else "red"
            console.print(
                f"[{status_color}]{status_icon} {case_name} finished in {case_metrics['duration_seconds']}s | "
                f"Spec: {case_metrics['m1_spec_valid']} ({case_metrics['m2_endpoints_count']} EPs) | "
                f"SDK: {case_metrics['m3_sdk_methods_count']} methods | "
                f"Build: {case_metrics['m5_scaffold_build']}[/{status_color}]"
            )
            if case_metrics["errors"]:
                for err in case_metrics["errors"]:
                    console.print(f"  [dim red]! {err}[/dim red]")
        else:
            # LIVE AUTONOMOUS AGENT EXECUTION
            plans_dir = case_dir / ".githeri" / "plans"
            backend_plans = [p for p in plans_dir.glob("*.plan.md") if not p.name.endswith(".ui.plan.md")]
            ui_plans = list(plans_dir.glob("*.ui.plan.md"))

            dest_plan = backend_plans[0] if backend_plans else None
            dest_ui_plan = ui_plans[0] if ui_plans else None

            agent_msg = (
                f"Execute full-stack implementation:\n"
                f"1) Backend plan: {dest_plan}\n"
                f"2) Frontend plan: {dest_ui_plan} (workspace: frontend)\n"
                f"Follow rules in AGENTS.md strictly. Work exclusively inside the current directory ('.'). "
                f"Do NOT search parent directories, other workspaces, or external log files. "
                f"Once automated tests (pytest) pass and frontend build (npm run build in frontend) exits code 0, conclude your turn immediately."
            )

            console.print(f"[bold cyan]⚡ Launching {args.agent} on {case_name}...[/bold cyan]")
            hermes_bin = shutil.which("hermes") or "hermes"
            agent_cmd = [hermes_bin, "chat", "-q", agent_msg]

            log_file = case_dir / "agent_execution.log"
            t_live = time.time()
            timed_out = False
            proc_returncode = 0
            with open(log_file, "w", encoding="utf-8") as lf:
                try:
                    agent_proc = subprocess.run(
                        agent_cmd,
                        cwd=str(case_dir),
                        stdout=lf,
                        stderr=subprocess.STDOUT,
                        timeout=args.timeout,
                    )
                    proc_returncode = agent_proc.returncode
                except subprocess.TimeoutExpired:
                    timed_out = True
                    proc_returncode = 124
                    lf.write(f"\n[HARNESS ERROR] Case {case_name} timed out after {args.timeout}s.\n")
                    console.print(f"[bold yellow]⚠ Case {case_name} timed out after {args.timeout}s. Capturing metrics...[/bold yellow]")

            live_duration = time.time() - t_live
            console.print(f"[dim]Agent process finished (code {proc_returncode}) in {round(live_duration, 1)}s[/dim]")

            # Run Dual Verification Gate & Metrics
            case_metrics = evaluate_live_case(case_dir, case_name, live_duration, worker_dir, githeri_bin)
            if timed_out:
                case_metrics["errors"].append(f"Timed out after {args.timeout}s")
            results.append(case_metrics)

            status_icon = "✔" if case_metrics.get("live_passed") else "✖"
            status_color = "green" if case_metrics.get("live_passed") else "red"
            console.print(
                f"[{status_color}]{status_icon} {case_name} LIVE completed in {case_metrics['duration_seconds']}s | "
                f"Parity: {case_metrics['m6_contract_parity']} | "
                f"Tests: {case_metrics['m7_tests_pass']} | "
                f"Frontend Build: {case_metrics['m10_frontend_build_clean']}[/{status_color}]"
            )
            if case_metrics["errors"]:
                for err in case_metrics["errors"]:
                    console.print(f"  [dim red]! {err}[/dim red]")

    # Write Scorecard JSON
    is_live_mode = args.live or args.eval_only
    summary_filename = "live_summary.json" if is_live_mode else "dry_run_summary.json"
    summary_file = runs_dir / summary_filename
    summary_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Generate Markdown Report
    report_title = "Full-Stack Live Agent Benchmark Report" if is_live_mode else "Full-Stack Dry-Run Runway Benchmark Report"
    report_filename = "BATCH_1_LIVE_REPORT.md" if is_live_mode else "BATCH_1_DRY_RUN_REPORT.md"
    md_report = [
        f"# {report_title} (Batch 1)",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Model**: `{args.model}` (`{args.provider}`)  ",
        f"**Driver**: `{args.agent}`  ",
        f"**Total Cases**: {len(results)}  ",
        "",
        "## Scorecard",
        "",
    ]

    passed_count = 0
    if not is_live_mode:
        md_report.append("| Case | M1: Spec Valid | M2: Endpoints | M3: TS SDK Methods | M4: UI Stage 0 | M5: Scaffold Build | Duration | Status |")
        md_report.append("|---|:---:|---:|---:|:---:|:---:|---:|:---:|")
        for r in results:
            passed = r.get("all_passed", False)
            if passed:
                passed_count += 1
            m1 = "PASS" if r.get("m1_spec_valid") else "FAIL"
            m4 = "PASS" if r.get("m4_ui_plan_stage0") else "FAIL"
            m5 = "PASS" if r.get("m5_scaffold_build") else "FAIL"
            status = "**PASS**" if passed else "**FAIL**"
            md_report.append(
                f"| `{r.get('case')}` | {m1} | {r.get('m2_endpoints_count', 0)} | {r.get('m3_sdk_methods_count', 0)} | {m4} | {m5} | {r.get('duration_seconds', 0)}s | {status} |"
            )
    else:
        md_report.append("| Case | M6: Parity | M7: Pytest | M9: Ruff | M10: UI Build | M11: Live API | M14: Zero Localhost | Duration | Status |")
        md_report.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|---:|:---:|")
        for r in results:
            passed = r.get("live_passed", False)
            if passed:
                passed_count += 1
            m6 = "PASS" if r.get("m6_contract_parity") else "FAIL"
            m7 = "PASS" if r.get("m7_tests_pass") else "FAIL"
            m9 = "PASS" if r.get("m9_static_hygiene") else "FAIL"
            m10 = "PASS" if r.get("m10_frontend_build_clean") else "FAIL"
            m11 = "PASS" if r.get("m11_live_api_binding") else "FAIL"
            m14 = "PASS" if r.get("m14_zero_hardcoded_localhost") else "FAIL"
            status = "**PASS**" if passed else "**FAIL**"
            md_report.append(
                f"| `{r.get('case')}` | {m6} | {m7} | {m9} | {m10} | {m11} | {m14} | {r.get('duration_seconds', 0)}s | {status} |"
            )

    rate = round(passed_count / len(results) * 100, 1) if results else 0
    md_report.extend([
        "",
        f"**Overall Pass Rate**: {passed_count}/{len(results)} ({rate}%)",
        "",
    ])

    report_path = runs_dir / report_filename
    report_path.write_text("\n".join(md_report), encoding="utf-8")

    # Render Table to Terminal
    table = Table(title=f"{report_title} (Batch 1)")
    table.add_column("Case", style="cyan")
    if not is_live_mode:
        table.add_column("M1: Valid Spec", justify="center")
        table.add_column("M2: Endpoints", justify="right")
        table.add_column("M3: TS SDK", justify="right")
        table.add_column("M4: Stage 0", justify="center")
        table.add_column("M5: Build", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Result", justify="center")
        for r in results:
            passed = r.get("all_passed", False)
            table.add_row(
                r.get("case", "unknown"),
                "✔" if r.get("m1_spec_valid") else "✖",
                str(r.get("m2_endpoints_count", 0)),
                f"{r.get('m3_sdk_methods_count', 0)} methods",
                "✔" if r.get("m4_ui_plan_stage0") else "✖",
                "✔" if r.get("m5_scaffold_build") else "✖",
                f"{r.get('duration_seconds', 0)}s",
                "[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]",
            )
    else:
        table.add_column("M6: Parity", justify="center")
        table.add_column("M7: Pytest", justify="center")
        table.add_column("M9: Ruff", justify="center")
        table.add_column("M10: UI Build", justify="center")
        table.add_column("M11: Live API", justify="center")
        table.add_column("M14: Localhost", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("Result", justify="center")
        for r in results:
            passed = r.get("live_passed", False)
            table.add_row(
                r.get("case", "unknown"),
                "✔" if r.get("m6_contract_parity") else "✖",
                "✔" if r.get("m7_tests_pass") else "✖",
                "✔" if r.get("m9_static_hygiene") else "✖",
                "✔" if r.get("m10_frontend_build_clean") else "✖",
                "✔" if r.get("m11_live_api_binding") else "✖",
                "✔" if r.get("m14_zero_hardcoded_localhost") else "✖",
                f"{r.get('duration_seconds', 0)}s",
                "[bold green]PASS[/bold green]" if passed else "[bold red]FAIL[/bold red]",
            )

    console.print("\n")
    console.print(table)
    console.print(f"\n[bold]Overall Pass Rate: {passed_count}/{len(results)} ({rate}%)[/bold]")
    console.print(f"Summary written to: [cyan]{summary_file}[/cyan]")
    console.print(f"Report written to: [cyan]{report_path}[/cyan]")


if __name__ == "__main__":
    run_fullstack_evaluation()
