#!/usr/bin/env python3
"""
LangGraph HITL dogfood CLI — interrupt/resume into Understanding Lab loop.

Examples:
  # Start run (pauses at interrupt; prints pending payload)
  python3 scripts/langgraph_dogfood.py start

  # Resume with decisions JSON file
  python3 scripts/langgraph_dogfood.py resume --thread-id <uuid> --decisions hitl/out/decisions.json

No secrets required. LangSmith keys optional via Infisical (LANGSMITH_API_KEY).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from langgraph.types import Command

from hitl.langgraph.findings import default_fixture_path
from hitl.langgraph.graph import compile_review_graph


def _sample_decisions(pending: list[dict]) -> dict:
    """Auto-agree stub for local smoke when --auto-resume is passed."""
    return {
        "decisions": [
            {
                "finding_id": p["finding_id"],
                "human_decision": "agree",
                "rationale": "Dogfood auto-resume — confirmed after lab review.",
                "status": "reviewed",
            }
            for p in pending
        ],
        "quiz_passed": True,
        "reviewer": "langgraph-dogfood",
    }


def cmd_start(args: argparse.Namespace) -> int:
    findings_path = Path(args.findings)
    if not findings_path.is_absolute():
        findings_path = ROOT / findings_path
    if not findings_path.exists():
        print(f"ERROR: findings not found: {findings_path}", file=sys.stderr)
        return 1

    thread_id = args.thread_id or str(uuid.uuid4())
    graph = compile_review_graph()
    config = {"configurable": {"thread_id": thread_id}}
    initial = {
        "job_id": args.job_id or findings_path.stem,
        "findings_path": str(findings_path),
    }

    interrupted = False
    interrupt_value = None
    for chunk in graph.stream(initial, config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            interrupted = True
            interrupt_value = chunk["__interrupt__"]
            break

    if not interrupted:
        print("ERROR: graph did not interrupt (unexpected for dogfood)", file=sys.stderr)
        return 1

    print(json.dumps({"thread_id": thread_id, "interrupt": _serialize_interrupt(interrupt_value)}, indent=2))

    if args.auto_resume:
        pending = interrupt_value[0].value.get("pending", []) if interrupt_value else []
        resume_payload = _sample_decisions(pending)
        final = graph.invoke(Command(resume=resume_payload), config)
        print(json.dumps({"status": final.get("status"), "locks_path": final.get("locks_path")}, indent=2))

    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    decisions_path = Path(args.decisions)
    if not decisions_path.is_absolute():
        decisions_path = ROOT / decisions_path
    payload = json.loads(decisions_path.read_text(encoding="utf-8"))

    graph = compile_review_graph()
    config = {"configurable": {"thread_id": args.thread_id}}
    final = graph.invoke(Command(resume=payload), config)
    print(json.dumps({"status": final.get("status"), "locks_path": final.get("locks_path")}, indent=2))
    return 0


def _serialize_interrupt(interrupt_tuple) -> dict:
    if not interrupt_tuple:
        return {}
    item = interrupt_tuple[0]
    return {"id": getattr(item, "id", None), "value": getattr(item, "value", item)}


def main() -> int:
    parser = argparse.ArgumentParser(description="LangGraph HITL dogfood for Scanner reviewer")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start review graph until HITL interrupt")
    start.add_argument(
        "--findings",
        default=str(default_fixture_path(ROOT)),
        help="Path to findings JSON (default: microworld fixture)",
    )
    start.add_argument("--job-id", default=None)
    start.add_argument("--thread-id", default=None, help="Checkpoint thread id (printed if omitted)")
    start.add_argument(
        "--auto-resume",
        action="store_true",
        help="Immediately resume with stub agree decisions (local smoke only)",
    )

    resume = sub.add_parser("resume", help="Resume interrupted thread with decisions JSON")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument("--decisions", required=True, help="JSON file with decisions[] payload")

    args = parser.parse_args()
    if args.command == "start":
        return cmd_start(args)
    if args.command == "resume":
        return cmd_resume(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
