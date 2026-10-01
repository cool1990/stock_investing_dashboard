"""Shared HTTP helpers: retries, SEC User-Agent, rate limit."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import requests

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Load KEY=VALUE pairs from repo-root .env if present (local only)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


_load_dotenv()

DEFAULT_BROWSER_UA = (
    "Mozilla/5.0 (compatible; stock_investing_dashboard/0.1; +https://github.com/cool1990/stock_investing_dashboard)"
)


def sec_user_agent() -> str:
    """SEC requires a descriptive User-Agent with contact email.

    Read from SEC_USER_AGENT env (GitHub Actions Variable or local .env).
    Expected value: ``stock_investing_dashboard raycao2023@gmail.com``
    """
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise RuntimeError(
            "SEC_USER_AGENT is not set. "
            "Configure it as a GitHub Actions Variable, or put it in a local .env file."
        )
    return ua


def get(
    url: str,
    *,
    sec: bool = False,
    timeout: float = 30.0,
    retries: int = 3,
    headers: Optional[dict] = None,
    min_interval: float = 0.0,
) -> requests.Response:
    """GET with exponential backoff. ``sec=True`` attaches SEC_USER_AGENT and enforces ≤10 req/s."""
    hdrs = dict(headers or {})
    if sec:
        hdrs.setdefault("User-Agent", sec_user_agent())
        hdrs.setdefault("Accept-Encoding", "gzip, deflate")
        if min_interval <= 0:
            min_interval = 0.11
    else:
        hdrs.setdefault("User-Agent", DEFAULT_BROWSER_UA)

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            if min_interval > 0:
                time.sleep(min_interval)
            resp = requests.get(url, headers=hdrs, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(2**attempt)
    assert last_err is not None
    raise last_err
