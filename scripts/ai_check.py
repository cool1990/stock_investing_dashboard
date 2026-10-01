#!/usr/bin/env python3
"""Validate ai/tasks/<id>/output/draft.json against schema; merge into pages on ok."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import read_json, write_json  # noqa: E402


def check_required(obj: dict, schema: dict) -> list[str]:
    errs = []
    for key in schema.get("required") or []:
        if key not in obj:
            errs.append(f"missing required field: {key}")
    return errs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="e.g. MU_call_FQ4-26")
    parser.add_argument("--apply", action="store_true", help="merge draft into page JSON")
    args = parser.parse_args()
    d = ROOT / "ai" / "tasks" / args.task
    draft_path = d / "output" / "draft.json"
    schema_path = d / "schema.json"
    if not draft_path.exists():
        print(f"missing {draft_path}", file=sys.stderr)
        return 1
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8")) if schema_path.exists() else {}
    errs = check_required(draft, schema)
    # No fabricated numeric guard: summary text length
    if "summary" in draft and isinstance(draft["summary"], dict):
        text = draft["summary"].get("text")
        if text is not None and len(str(text)) < 10:
            errs.append("summary.text too short")
    report = {"ok": not errs, "errors": errs}
    (d / "output" / "check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if errs:
        print("FAIL", errs)
        return 1
    print("OK")
    if args.apply:
        meta = json.loads((d / "task.json").read_text(encoding="utf-8"))
        ticker = meta["ticker"]
        kind = meta["kind"]
        period = meta["period"]
        if kind == "call":
            out = ROOT / "data" / "pages" / ticker / "call.json"
            write_json(out, draft)
            write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "call.json", draft)
            write_json(ROOT / "data" / "pages" / ticker / f"call-{period}.json", draft)
            print(f"applied → {out}")
        elif kind == "review":
            page = read_json(ROOT / "data" / "pages" / ticker / "review.json", default={}) or {}
            if draft.get("summary"):
                page.setdefault("verdict", {})["summary"] = draft["summary"]
            if draft.get("watch"):
                page.setdefault("verdict", {})["watch"] = draft["watch"]
            if draft.get("talk"):
                page["talk"] = draft["talk"]
            page["ai_status"] = "ai_applied"
            write_json(ROOT / "data" / "pages" / ticker / "review.json", page)
            write_json(ROOT / "web" / "public" / "data" / "pages" / ticker / "review.json", page)
            print("applied review AI fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
