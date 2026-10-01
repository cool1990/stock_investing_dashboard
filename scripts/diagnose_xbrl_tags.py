#!/usr/bin/env python3
"""List us-gaap tags present in SEC companyfacts for a ticker.

Writes ``data/raw/<T>/xbrl_tags.txt`` (committed for audit) and prints candidates
useful for filling ``config/companies/<T>.yaml`` → ``xbrl_map``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.lib.edgar import fetch_companyfacts, list_tag_coverage  # noqa: E402
from scripts.lib.io import load_company, update_status  # noqa: E402

# Keywords that help operators pick tags for the financials map
HINT_KEYWORDS = [
    "Revenue",
    "CostOf",
    "GrossProfit",
    "ResearchAndDevelopment",
    "SellingGeneral",
    "OperatingIncome",
    "NetIncome",
    "EarningsPerShare",
    "WeightedAverage",
    "CashAndCashEquivalents",
    "ShortTermInvestments",
    "AvailableForSale",
    "AccountsReceivable",
    "Inventory",
    "LongTermInvestments",
    "PropertyPlantAndEquipment",
    "Assets",
    "Debt",
    "Liabilities",
    "StockholdersEquity",
    "NetCashProvidedByUsedInOperating",
    "PaymentsToAcquirePropertyPlant",
    "Depreciation",
    "ShareBasedCompensation",
    "PaymentsForRepurchase",
    "PaymentsOfDividends",
    "RepaymentsOf",
    "ContractWithCustomerLiability",
    "Interest",
    "IncomeTax",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="MU")
    parser.add_argument("--force", action="store_true", help="re-download companyfacts")
    args = parser.parse_args()
    ticker = args.ticker.upper()
    cfg = load_company(ticker)
    cik = cfg["cik"]

    try:
        facts = fetch_companyfacts(cik, ticker=ticker, force=args.force)
        update_status("sec_companyfacts", True, f"CIK{int(cik):010d}")
    except Exception as e:  # noqa: BLE001
        update_status("sec_companyfacts", False, str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    coverage = list_tag_coverage(facts)
    out = ROOT / "data" / "raw" / ticker / "xbrl_tags.txt"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# us-gaap tags for {ticker} (CIK {int(cik):010d})",
        f"# source: data.sec.gov companyfacts",
        f"# columns: n_filings | units | fps | end_min | end_max | tag",
        "",
    ]
    for row in coverage:
        lines.append(
            f"{row['n']:5d}  {row['units']:<20}  {row['fps']:<20}  "
            f"{row['end_min']}..{row['end_max']}  {row['tag']}"
        )

    # Hint section
    lines.append("")
    lines.append("# --- candidates matching financials keywords ---")
    for row in coverage:
        if any(k.lower() in row["tag"].lower() for k in HINT_KEYWORDS):
            lines.append(f"# {row['n']:5d}  {row['tag']}  ({row['units']}; {row['fps']})")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(coverage)} tags)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
