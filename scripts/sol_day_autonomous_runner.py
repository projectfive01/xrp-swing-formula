#!/usr/bin/env python3
"""
SOL Day v3 — Autonomous Runner (paper default, optional live)

Entry guards (anti-printer):
  - Chicago calendar for daily halt / consumed setups
  - FVG bar age vs signal_fresh_minutes
  - Reject mark through stop, past 3R, or > max_entry_distance_r from mid
  - Consume direction:mid:fvg_idx so the same FVG cannot reprint after a close
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.error import URLError

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts import sol_day_runner_trade as trade
from scripts.sol_day_runner_detect import detect_setup
from scripts.sol_day_runner_io import (
    fetch_klines,
    fetch_price,
    kill_on,
    load_cfg,
    load_dotenv,
    p,
    session_tz,
    trading_date,
)


def loop_once(cfg: dict) -> None:
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] cycle live={trade.LIVE_MODE}")
    if kill_on(cfg):
        print("  KILL SWITCH ON")
    try:
        klines = fetch_klines(cfg["symbol"], cfg.get("timeframe", "15m"), 300)
        price = float(klines[-1][4])
        try:
            price = fetch_price(cfg["symbol"])
        except Exception:
            pass
        print(f"  price={price:.4f}")

        trade.manage_open(cfg, price)

        setup = detect_setup(klines, float(cfg.get("fvg_min_atr_multiple", 0.6)))
        sig = trade.write_signal(cfg, setup)
        extra = f" {sig['skip_reason']}" if sig.get("skip_reason") else ""
        age = sig.get("setup_age_minutes")
        age_s = f" age={age}m" if age is not None else ""
        print(f"  signal={sig['status']} dir={sig.get('direction')}{age_s}{extra}")

        trade.try_open(cfg, sig, price)
    except URLError as e:
        print(f"  network error: {e}")
    except Exception as e:
        print(f"  error: {e}")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=None)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Place real Binance orders (requires BINANCE_LIVE=1 and API keys)",
    )
    args = parser.parse_args()
    trade.LIVE_MODE = bool(args.live)
    if trade.LIVE_MODE and os.environ.get("BINANCE_LIVE", "0") != "1":
        print("ERROR: --live requires BINANCE_LIVE=1 in environment / .env")
        sys.exit(1)

    cfg = load_cfg()
    poll = args.poll or int(cfg.get("poll_seconds", 120))
    print("SOL Day autonomous runner")
    print(f"  mode={'LIVE' if trade.LIVE_MODE else 'PAPER'} poll={poll}s unit=${cfg['equity_unit_usd']}")
    print(f"  kill_switch={p('kill_switch', cfg)}")
    print(f"  trading_date={trading_date(cfg)} tz={session_tz(cfg)}")
    if trade.LIVE_MODE:
        print(f"  BINANCE_ENV={os.environ.get('BINANCE_ENV', 'testnet')}")

    while True:
        loop_once(cfg)
        if args.once:
            break
        time.sleep(poll)


if __name__ == "__main__":
    main()
