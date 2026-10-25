#!/usr/bin/env python3
"""Drive the Githeri MCP server over real stdio MCP (not the CLI).

Used by the evaluation harness to exercise the full intake state machine:
start -> next_question -> answer -> ... -> validate -> preview -> confirm -> compile -> submit.

Every tool call and its raw response is written to a JSONL transcript so the
measurements in evaluation/RESULTS.md are reproducible and auditable.

Usage:
  .venv/bin/python evaluation/tools/intake_drive.py \
      --project-dir <dir> \
      --name <session-name> \
      --problem "<problem statement>" \
      --mode guided \
      --answers-file <json> \
      --out <transcript.jsonl>
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

GITHERI_BIN = str(Path(__file__).resolve().parents[2] / ".venv" / "bin" / "githeri")


def parse_result(result: Any) -> Any:
    """MCP tool results come back as text content holding a JSON string."""
    for attr in ("structuredContent", "structured_content"):
        val = getattr(result, attr, None)
        if isinstance(val, dict) and val.get("result"):
            inner = val["result"]
            if isinstance(inner, str):
                try:
                    return json.loads(inner)
                except json.JSONDecodeError:
                    return inner
            return inner
    text_parts = []
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            text_parts.append(text)
    raw = "\n".join(text_parts)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


class Driver:
    def __init__(self, session: ClientSession, transcript: Path) -> None:
        self.session = session
        self.transcript = transcript
        self.timeline: list[dict[str, Any]] = []
        self._fh = transcript.open("w")

    def log(self, kind: str, **payload: Any) -> None:
        rec = {"kind": kind, "ts": time.time(), **payload}
        self.timeline.append(rec)
        self._fh.write(json.dumps(rec, default=str) + "\n")
        self._fh.flush()

    async def call(self, tool: str, args: dict[str, Any]) -> Any:
        t0 = time.perf_counter()
        result = await self.session.call_tool(tool, args)
        dt = time.perf_counter() - t0
        parsed = parse_result(result)
        is_error = bool(getattr(result, "isError", False))
        self.log("call", tool=tool, args=args, ok=not is_error,
                 seconds=round(dt, 3), response=parsed)
        return parsed

    def close(self) -> None:
        self._fh.close()


async def run(args: argparse.Namespace) -> int:
    project_dir = str(Path(args.project_dir).resolve())
    answers: dict[str, str] = {}
    if args.answers_file and Path(args.answers_file).exists():
        answers = json.loads(Path(args.answers_file).read_text())

    env = dict(os.environ)
    # Githeri reads its own credentials from ~/.githeri/credentials.json; pass the
    # shell env through so GEMINI_API_KEY / GITHERI_API_KEY reach the subprocess.
    params = StdioServerParameters(
        command=GITHERI_BIN,
        args=["mcp"],
        env=env,
        cwd=project_dir,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            driver = Driver(session, out)
            driver.log("initialize", server_info=getattr(init, "server_info", None),
                       protocol_version=getattr(init, "protocol_version", None))

            tools = await session.list_tools()
            driver.log("list_tools", count=len(tools.tools),
                       names=[t.name for t in tools.tools])

            start = await driver.call("githeri_intake_start", {
                "name": args.name,
                "problem_statement": args.problem,
                "project_dir": project_dir,
                "mode": args.mode,
            })
            session_id = start.get("session_id")
            if not session_id:
                driver.log("fatal", reason="intake_start did not return session_id",
                           response=start)
                driver.close()
                return 2

            baseline = {
                "readiness_score": start.get("readiness_score"),
                "scores": start.get("scores"),
                "coaching_findings": start.get("coaching_findings"),
                "clear_spec_assessment": start.get("clear_spec_assessment"),
            }
            driver.log("baseline", **baseline)

            asked: list[dict[str, Any]] = []
            default_answer = args.default_answer
            max_questions = args.max_questions

            for _ in range(max_questions):
                nxt = await driver.call("githeri_intake_next_question", {
                    "session_id": session_id, "project_dir": project_dir})
                question = nxt.get("next_question") if isinstance(nxt, dict) else None
                if not question:
                    driver.log("no_more_questions", response=nxt)
                    break
                qid = question.get("id")
                tier = question.get("ambiguity_tier")
                asked.append({
                    "id": qid, "stage": question.get("stage"), "tier": tier,
                    "severity": question.get("severity"),
                    "question": question.get("question"),
                })
                driver.log("question_asked", **asked[-1])

                text = answers.get(qid)
                if text is None:
                    text = question.get("default_proposal") or default_answer
                    source = "default_proposal" if question.get("default_proposal") else "fallback"
                else:
                    source = "fixture"

                if args.stop_after_first and len(asked) >= 1:
                    driver.log("stop_after_first", qid=qid)
                    break

                await driver.call("githeri_intake_answer", {
                    "session_id": session_id,
                    "question_id": qid,
                    "answer_text": text,
                    "project_dir": project_dir,
                })
                driver.log("answered", qid=qid, source=source, text=text)

            validate = await driver.call("githeri_intake_validate", {
                "session_id": session_id, "project_dir": project_dir})
            driver.log("validate", response=validate)

            preview = await driver.call("githeri_intake_preview", {
                "session_id": session_id, "project_dir": project_dir, "format": "yaml"})
            driver.log("preview", response=preview)

            confirm = await driver.call("githeri_intake_confirm", {
                "session_id": session_id, "project_dir": project_dir})
            driver.log("confirm", response=confirm)

            compile_unforced = await driver.call("githeri_intake_compile", {
                "session_id": session_id, "project_dir": project_dir, "force": False})
            driver.log("compile_unforced", response=compile_unforced)

            compiled_ok = False
            if isinstance(compile_unforced, dict) and compile_unforced.get("ok"):
                compiled_ok = True
            else:
                compile_forced = await driver.call("githeri_intake_compile", {
                    "session_id": session_id, "project_dir": project_dir, "force": True})
                driver.log("compile_forced", response=compile_forced)
                compiled_ok = bool(isinstance(compile_forced, dict) and compile_forced.get("ok"))

            # Submit: force=False keeps the adapter on the direct canonical path
            # (no LLM re-prompting). force=True routes into LLM spec generation, which
            # has no provider parameter on the MCP tool and therefore always hits the
            # unavailable 'bundled' engine. Recorded as a defect, worked around here.
            submit = None
            if compiled_ok:
                submit = await driver.call("githeri_intake_submit", {
                    "session_id": session_id, "project_dir": project_dir, "force": False})
                driver.log("submit_direct", response=submit)
                if not (isinstance(submit, dict) and submit.get("ok")):
                    submit_forced = await driver.call("githeri_intake_submit", {
                        "session_id": session_id, "project_dir": project_dir, "force": True})
                    driver.log("submit_forced", response=submit_forced)

            summary = {
                "session_id": session_id,
                "questions_asked": len(asked),
                "questions": asked,
                "baseline": baseline,
                "validate": validate,
                "compile_unforced": compile_unforced,
                "compiled": compiled_ok,
                "submit": submit,
            }
            driver.log("summary", **summary)
            Path(str(out) + ".summary.json").write_text(json.dumps(summary, indent=2, default=str))
            driver.close()
            print(json.dumps(summary, indent=2, default=str)[:4000])
            return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--problem", required=True)
    ap.add_argument("--mode", default="guided")
    ap.add_argument("--answers-file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--default-answer", default="Not specified; use a sensible default and record it as an assumption.")
    ap.add_argument("--max-questions", type=int, default=12)
    ap.add_argument("--stop-after-first", action="store_true")
    args = ap.parse_args()
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
