#!/usr/bin/env python3
"""
SOL 1m RSI-S CORE — paper runner.

Implementation rules (not formula):
  - RSI/ATR computed on CLOSED 1m candles only. Forming bar never enters RSI.
  - Signal evaluated once per newly closed 1m bar.
  - Live ticker is used only to manage an open position.
  - Data: Binance.US first, public vision fallback on timeout.
  - This runner does NOT use SOL Day ChoCh / FVG / structural invalidation.

Usage:
  python scripts/sol_1m_rsi_core_paper.py
  python scripts/sol_1m_rsi_core_paper.py --once
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backtest.core.sol_1m_rsi_core import (  # noqa: E402
    ATR_PERIOD,
    DAILY_CAP_R,
    PAPER_EQUITY_START,
    RISK_PCT,
    RSI_PERIOD,
    SESSION_HOURS_UTC,
    in_session,
    levels,
    signal_from_closed_rsi,
    wilder_atr,
    wilder_rsi,
)

SYMBOL = "SOLUSDT"
POLL_SEC = 15
KILL = REPO / "data" / "KILL_SWITCH.txt"
STATE = REPO / "data" / "sol_1m_rsi_core_state.json"
TRADES = REPO / "data" / "sol_1m_rsi_core_paper_trades.jsonl"
KLINE_LIMIT = 200

ENDPOINTS = (
    "https://api.binance.us/api/v3",
    "https://data-api.binance.vision/api/v3",
    "https://api.binance.com/api/v3",
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def log(msg: str) -> None:
    print(f"[{now_utc().strftime('%H:%M:%S')}] {msg}", flush=True)


def kill_on() -> bool:
    if not KILL.exists():
        return False
    return KILL.read_text().strip().upper().startswith("ON")


def http_get(path: str, timeout: int = 12) -> object:
    last_err = None
    for base in ENDPOINTS:
        url = f"{base}{path}"
        req = Request(url, headers={"User-Agent": "sol-1m-rsi-core/1.0"})
        try:
            with urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except (URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            continue
    raise RuntimeError(f"all endpoints failed: {last_err}")


def fetch_closed_klines() -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    raw = http_get(f"/klines?symbol={SYMBOL}&interval=1m&limit={KLINE_LIMIT}")
    closed = raw[:-1] if raw else raw
    highs = np.array([float(c[2]) for c in closed])
    lows = np.array([float(c[3]) for c in closed])
    closes = np.array([float(c[4]) for c in closed])
    last_open_ms = int(closed[-1][0])
    return highs, lows, closes, last_open_ms


def fetch_price() -> float:
    data = http_get(f"/ticker/price?symbol={SYMBOL}", timeout=8)
    return float(data["price"])


def load_state() -> dict:
    if STATE.exists():
        try:
            st = json.loads(STATE.read_text())
        except json.JSONDecodeError:
            st = {}
    else:
        st = {}
    today = now_utc().strftime("%Y-%m-%d")
    if st.get("date") != today:
        st = {
            "date": today,
            "equity": float(st.get("equity", PAPER_EQUITY_START) or PAPER_EQUITY_START),
            "position": None,
            "day_r": 0.0,
            "last_bar_ms": None,
            "last_signal_bar_ms": None,
        }
    st.setdefault("equity", PAPER_EQUITY_START)
    st.setdefault("position", None)
    st.setdefault("day_r", 0.0)
    st.setdefault("last_bar_ms", None)
    st.setdefault("last_signal_bar_ms", None)
    return st


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2, default=str))


def append_trade(row: dict) -> None:
    TRADES.parent.mkdir(parents=True, exist_ok=True)
    with TRADES.open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")


def close_pos(st: dict, price: float, reason: str, r_mult: float) -> None:
    pos = st["position"]
    pnl = r_mult * pos["risk_usd"]
    st["equity"] = round(float(st["equity"]) + pnl, 2)
    st["day_r"] = round(float(st["day_r"]) + r_mult, 2)
    append_trade(
        {
            "ts": now_utc().isoformat(),
            "side": pos["side"],
            "entry": pos["entry"],
            "exit": round(price, 4),
            "stop": pos["stop"],
            "tgt": pos["tgt"],
            "r": r_mult,
            "reason": reason,
            "equity": st["equity"],
            "day_r": st["day_r"],
        }
    )
    log(f"EXIT {reason} r={r_mult:+.2f} eq=${st['equity']:.0f}")
    st["position"] = None


def manage(st: dict, price: float) -> None:
    pos = st.get("position")
    if not pos:
        return
    side = pos["side"]
    r_val = pos["r_value"]
    if side == "LONG":
        u = (price - pos["entry"]) / r_val
        hit_stop = price <= pos["stop"]
        hit_tgt = price >= pos["tgt"]
    else:
        u = (pos["entry"] - price) / r_val
        hit_stop = price >= pos["stop"]
        hit_tgt = price <= pos["tgt"]
    if hit_tgt:
        close_pos(st, price, "Target 2R", 2.0)
    elif hit_stop:
        close_pos(st, price, "Stop 1R", -1.0)
    else:
        log(f"IN {pos['entry']:.2f} uPnL={u:+.2f}R")


def try_entry(st: dict, side: str, close_px: float, atr: float, bar_ms: int, rsi: float) -> None:
    if st.get("position"):
        return
    if st.get("last_signal_bar_ms") == bar_ms:
        return
    if float(st["day_r"]) <= -DAILY_CAP_R:
        log(f"day cap {st['day_r']:+.2f}R — no new entries")
        return
    if kill_on():
        log("kill switch ON — no new entries")
        return
    lv = levels(side, close_px, atr)
    if not lv:
        return
    equity = float(st["equity"])
    risk_usd = equity * RISK_PCT
    st["position"] = {
        "side": side,
        "entry": close_px,
        "stop": lv["stop"],
        "tgt": lv["tgt"],
        "r_value": lv["r_value"],
        "risk_usd": risk_usd,
        "bar_ms": bar_ms,
        "rsi": rsi,
    }
    st["last_signal_bar_ms"] = bar_ms
    log(
        f"PAPER {side} @ {close_px:.2f} stop={lv['stop']:.2f} "
        f"tgt={lv['tgt']:.2f} rsi={rsi:.1f} atr={atr:.4f}"
    )


def cycle() -> None:
    st = load_state()
    hour = now_utc().hour
    sess = in_session(hour)

    highs, lows, closes, bar_ms = fetch_closed_klines()
    rsi_arr = wilder_rsi(closes, RSI_PERIOD)
    atr_arr = wilder_atr(highs, lows, closes, ATR_PERIOD)
    rsi = float(rsi_arr[-1])
    atr = float(atr_arr[-1])
    close_px = float(closes[-1])
    try:
        px = fetch_price()
    except Exception:
        px = close_px

    new_bar = st.get("last_bar_ms") != bar_ms
    st["last_bar_ms"] = bar_ms

    if st.get("position"):
        manage(st, px)
        save_state(st)
        return

    sig = signal_from_closed_rsi(rsi) if sess and np.isfinite(rsi) else "WAIT"
    if not sess:
        reason = "WAIT/sess"
    elif not np.isfinite(rsi):
        reason = "WAIT/rsi-warmup"
    elif sig == "WAIT":
        reason = "WAIT"
    else:
        reason = sig

    log(
        f"px={px:.2f} close1m={close_px:.2f} rsi={rsi:.1f} atr={atr:.4f} "
        f"sess={sess} signal={reason} dayR={float(st['day_r']):+.2f}"
    )

    if new_bar and sess and sig in ("LONG", "SHORT") and np.isfinite(atr):
        try_entry(st, sig, close_px, atr, bar_ms, rsi)

    save_state(st)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=POLL_SEC)
    args = parser.parse_args()

    print("SOL 1m RSI-S CORE paper runner")
    print(f"  mode=PAPER  hours={list(SESSION_HOURS_UTC)} UTC  f={RISK_PCT*100:.1f}%")
    print(f"  kill={KILL}")
    print(f"  daily cap={DAILY_CAP_R:.1f}R")
    print("  RSI/ATR on CLOSED 1m bars only — not SOL Day structure")

    while True:
        try:
            cycle()
        except Exception as e:
            log(f"data error: {e}")
        if args.once:
            break
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
