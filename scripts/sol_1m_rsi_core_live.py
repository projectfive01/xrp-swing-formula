#!/usr/bin/env python3
"""
SOL 1m RSI-S CORE — live wrapper.

Default is still paper accounting. Real orders only with:
  BINANCE_LIVE=1 python scripts/sol_1m_rsi_core_live.py --live

Live risk cap stays $2. Formula thresholds are imported, not duplicated.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backtest.core.sol_1m_rsi_core import PAPER_EQUITY_START, RISK_PCT  # noqa: E402

RISK_USD_CAP = 2.00
PAPER_EQUITY_START = PAPER_EQUITY_START
PAPER_RISK_PCT = RISK_PCT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=15)
    args = parser.parse_args()

    if args.live and os.environ.get("BINANCE_LIVE", "0") != "1":
        print("ERROR: --live requires BINANCE_LIVE=1")
        sys.exit(1)

    if args.live:
        print(f"LIVE mode armed — hard risk cap ${RISK_USD_CAP:.2f}")
        print("Live order placement is not wired in this patch.")
        print("Run the paper runner until fills + 1m RSI behavior are verified.")
        sys.exit(2)

    from scripts.sol_1m_rsi_core_paper import main as paper_main

    sys.argv = [sys.argv[0]]
    if args.once:
        sys.argv.append("--once")
    sys.argv.extend(["--poll", str(args.poll)])
    paper_main()


if __name__ == "__main__":
    main()
