#!/usr/bin/env python3
"""Generate data/pages/calendar.ics from watchlist.json calendar entries."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import read_json  # noqa: E402


def to_utc_stamp(day: str, hour_et: int, minute: int = 0) -> str:
    # Approximate ET as UTC-4 (EDT); good enough for calendar export
    dt = datetime.fromisoformat(day) + timedelta(hours=hour_et + 4, minutes=minute)
    dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    wl = read_json(ROOT / "data" / "pages" / "watchlist.json", default={}) or {}
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//stock_investing_dashboard//CN",
        "CALSCALE:GREGORIAN",
    ]
    for ev in wl.get("calendar") or []:
        day = ev.get("d")
        if not day:
            continue
        t = ev.get("t") or ""
        q = ev.get("q") or ""
        timing = ev.get("timing") or "盘后"
        hour = 16 if "后" in timing else 8
        start = to_utc_stamp(day, hour, 5 if hour == 16 else 0)
        end = to_utc_stamp(day, hour + 1, 5 if hour == 16 else 0)
        cons = ev.get("cons_eps")
        desc = f"共识 EPS {cons}" if cons is not None else "共识待补"
        uid = f"{t}-{q}-{day}@stock_investing_dashboard"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:{t} {q} 财报（{timing}）",
            f"DESCRIPTION:{desc}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    text = "\r\n".join(lines) + "\r\n"
    for path in (
        ROOT / "data" / "pages" / "calendar.ics",
        ROOT / "web" / "public" / "data" / "pages" / "calendar.ics",
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print("wrote calendar.ics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
