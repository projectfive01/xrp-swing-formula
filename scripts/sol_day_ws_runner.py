#!/usr/bin/env python3
"""
SOL Day v3 — WebSocket-driven autonomous runner

- Streams SOLUSDT 15m kline + trade ticks via Binance WS
- On every kline close: run locked formula + open paper/live if READY
- On every trade tick: mark-to-market open positions (stop / 3R / 4R)
- Optional user data stream when --live (order fill events)

Requires: pip install websocket-client numpy

Usage:
  python scripts/sol_day_ws_runner.py
  python scripts/sol_day_ws_runner.py --once-closed   # exit after first closed kline cycle
  BINANCE_LIVE=1 python scripts/sol_day_ws_runner.py --live
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# Reuse detection + trade management from autonomous runner
from scripts import sol_day_autonomous_runner as ar
from execution.binance_ws import BinancePublicStream, BinanceUserStream, StreamCallbacks


def main() -> None:
    ar.load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--once-closed", action="store_true", help="Exit after one closed-kline cycle")
    parser.add_argument("--symbol", default="SOLUSDT")
    args = parser.parse_args()

    if args.live and os.environ.get("BINANCE_LIVE", "0") != "1":
        print("ERROR: --live requires BINANCE_LIVE=1")
        sys.exit(1)

    ar.LIVE_MODE = bool(args.live)
    cfg = ar.load_cfg()
    cfg["symbol"] = args.symbol

    print("SOL Day WS runner")
    print(f"  mode={'LIVE' if ar.LIVE_MODE else 'PAPER'} env={os.environ.get('BINANCE_ENV', 'testnet')}")
    print(f"  symbol={cfg['symbol']} kill={ar.p('kill_switch', cfg)}")

    state = {"closed_cycles": 0, "last_price": None}

    def on_trade(t: dict) -> None:
        state["last_price"] = t["price"]
        try:
            ar.manage_open(cfg, t["price"])
        except Exception as e:
            print(f"  manage error: {e}")

    def on_kline(k: dict) -> None:
        state["last_price"] = k["close"]
        if not k["is_closed"]:
            # light MTM on forming candle
            try:
                ar.manage_open(cfg, k["close"])
            except Exception:
                pass

    def on_kline_closed(k: dict) -> None:
        print(f"\n[kline closed] {k['interval']} close={k['close']:.4f}")
        try:
            # Full cycle: fetch REST history for structure detection (WS alone lacks depth of history)
            klines = ar.fetch_klines(cfg["symbol"], cfg.get("timeframe", "15m"), 300)
            price = float(k["close"])
            ar.manage_open(cfg, price)
            setup = ar.detect_setup(klines, float(cfg.get("fvg_min_atr_multiple", 0.6)))
            sig = ar.write_signal(cfg, setup)
            print(f"  signal={sig['status']} dir={sig.get('direction')}")
            ar.try_open(cfg, sig, price)
            state["closed_cycles"] += 1
        except Exception as e:
            print(f"  cycle error: {e}")

    def on_user(msg: dict) -> None:
        et = msg.get("e")
        if et == "executionReport":
            print(
                f"  [user] order {msg.get('i')} {msg.get('S')} {msg.get('o')} "
                f"status={msg.get('X')} qty={msg.get('q')} price={msg.get('p')}"
            )
        elif et == "outboundAccountPosition":
            print("  [user] account position update")

    def on_error(e: Exception) -> None:
        print(f"  ws error: {e}")

    def on_connected() -> None:
        print("  ws connected")

    cb = StreamCallbacks()
    cb.on_trade = on_trade
    cb.on_kline = on_kline
    cb.on_kline_closed = on_kline_closed
    cb.on_error = on_error
    cb.on_connected = on_connected

    sym = cfg["symbol"].lower()
    interval = cfg.get("timeframe", "15m")
    streams = [f"{sym}@kline_{interval}", f"{sym}@trade"]
    pub = BinancePublicStream(streams, cb)
    pub.start()

    user = None
    if args.live:
        ucb = StreamCallbacks()
        ucb.on_user = on_user
        ucb.on_error = on_error
        try:
            user = BinanceUserStream(ucb)
            user.start()
            print("  user data stream starting...")
        except Exception as e:
            print(f"  user stream not started: {e}")

    # Seed one REST cycle so we don't wait a full 15m for first signal
    try:
        ar.loop_once(cfg)
    except Exception as e:
        print(f"  seed cycle error: {e}")

    try:
        while True:
            if args.once_closed and state["closed_cycles"] >= 1:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        pub.stop()
        if user:
            user.stop()


if __name__ == "__main__":
    main()
