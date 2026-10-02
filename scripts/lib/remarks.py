"""Segment company prepared-remarks PDFs into speaker paragraphs."""

from __future__ import annotations

import re
from pathlib import Path

# "SANJAY MEHROTRA, CHAIRMAN AND CHIEF EXECUTIVE OFFICER"
_SPEAKER = re.compile(
    r"^([A-Z][A-Z .'\-]{1,60}),\s+([A-Z][A-Z0-9 /&,'\-]{2,120})$"
)
_PAGE_HEADER = re.compile(
    r"^(Micron Technology, Inc\.|Fiscal Q\d \d{4} Earnings Call Prepared Remarks)$",
    re.I,
)


def extract_pdf_text(path: Path) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def initials(name: str) -> str:
    bits = [b for b in re.split(r"\s+", name.strip()) if b and b.lower() not in {"and", "of"}]
    if not bits:
        return "?"
    return "".join(b[0] for b in bits if b[0].isalpha())[:3].upper()


def role_zh(role_en: str) -> str:
    r = role_en.upper()
    if "CHIEF EXECUTIVE" in r or re.search(r"\bCEO\b", r):
        return "董事长、总裁兼 CEO" if "CHAIRMAN" in r else "首席执行官"
    if "CHIEF FINANCIAL" in r or re.search(r"\bCFO\b", r):
        return "执行副总裁兼 CFO"
    if "INVESTOR RELATIONS" in r:
        return "投资者关系与财务副总裁"
    return role_en.title()


def segment_prepared_remarks(text: str) -> tuple[list[dict], list[dict]]:
    """Return (executives, paragraphs) from a prepared-remarks transcript."""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not _PAGE_HEADER.match(ln)]

    executives: list[dict] = []
    seen: set[str] = set()
    paras: list[dict] = []
    cur_who = "Operator"
    cur_role = "主持人"
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        body = " ".join(buf).strip()
        buf = []
        if not body:
            return
        paras.append(
            {
                "id": f"p{len(paras) + 1}",
                "src": "remarks",
                "ts": None,
                "who": cur_who,
                "role": cur_role,
                "en": body,
                "zh": None,
            }
        )

    for line in lines:
        m = _SPEAKER.match(line)
        if m:
            flush()
            cur_who = m.group(1).title().replace("  ", " ")
            cur_role = m.group(2).title().replace("  ", " ")
            key = cur_who.lower()
            if key not in seen:
                seen.add(key)
                executives.append(
                    {
                        "ini": initials(cur_who),
                        "name": cur_who,
                        "role_zh": role_zh(m.group(2)),
                        "role_en": cur_role,
                    }
                )
            continue
        buf.append(line)
    flush()
    return executives, paras
