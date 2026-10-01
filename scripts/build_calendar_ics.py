#!/usr/bin/env python3
"""Generate data/pages/calendar.ics from watchlist.json calendar entries."""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.io import read_json  # noqa: E402


def nth_sunday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    first_sun = 1 + (6 - first.weekday()) % 7
    return date(year, month, first_sun + 7 * (n - 1))


def et_offset_hours(day: date) -> int:
    """Hours to add to an ET clock time to reach UTC. EDT is UTC−4."""
    start = nth_sunday(day.year, 3, 2)
    end = nth_sunday(day.year, 11, 1)
    if start <= day < end:
        return 4
    return 5


def to_utc_stamp(day: str, hour_et: int, minute: int = 0) -> str:
    day_d = date.fromisoformat(day)
    dt = datetime.fromisoformat(day) + timedelta(hours=hour_et + et_offset_hours(day_d), minutes=minute)
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
        timing = ev.get("timing") or "after_close"
        after = timing in ("after_close", "盘后") or "后" in str(timing)
        hour = 16 if after else 8
        label = "盘后" if after else "盘前"
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
            f"SUMMARY:{t} {q} 财报（{label}{'，预估' if ev.get('estimated') else ''}）",
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
