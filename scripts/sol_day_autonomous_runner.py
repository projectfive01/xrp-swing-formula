#!/usr/bin/env python3
"""
SOL Day v3 — Autonomous Runner (paper default, optional live)

Self-contained loop:
  1. Respect kill switch + daily loss limit
  2. Fetch Binance 15m klines
  3. Detect Structure + ChoCh + first FVG ≥ 0.6×ATR (locked formula)
  4. Write local signal file
  5. Open paper trade when READY (one at a time)
  6. If --live and BINANCE_LIVE=1: also place LIMIT + STOP on Binance
  7. Manage open trade on every loop (stop / 3R / 4R)

Usage:
  python scripts/sol_day_autonomous_runner.py
  python scripts/sol_day_autonomous_runner.py --once
  python scripts/sol_day_autonomous_runner.py --poll 60
  BINANCE_LIVE=1 python scripts/sol_day_autonomous_runner.py --live   # testnet/mainnet per .env

Kill switch:
  echo OFF > data/KILL_SWITCH.txt
  echo ON  > data/KILL_SWITCH.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
CFG_PATH = REPO / "backtest" / "config" / "sol_day_runtime.yaml"

# runtime flag set in main()
LIVE_MODE = False


def load_dotenv() -> None:
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_cfg() -> dict:
    defaults = {
        "symbol": "SOLUSDT",
        "timeframe": "15m",
        "poll_seconds": 120,
        "equity_unit_usd": 1000.0,
        "kelly_fraction": 0.045,
        "max_risk_pct": 0.05,
        "daily_loss_limit_pct": 0.08,
        "fvg_min_atr_multiple": 0.60,
        "signal_fresh_minutes": 90,
        "paths": {
            "kill_switch": "data/KILL_SWITCH.txt",
            "open_trades": "data/sol_day_open_trades.json",
            "closed_trades": "data/sol_day_paper_trades.jsonl",
            "latest_signal": "data/sol_day_latest_signal.json",
            "daily_state": "data/sol_day_daily_state.json",
        },
    }
    if not CFG_PATH.exists():
        return defaults
    text = CFG_PATH.read_text()
    cfg = dict(defaults)
    section = None
    for raw in text.splitlines():
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            key = line[:-1].strip()
            if key == "paths":
                section = "paths"
                cfg.setdefault("paths", {})
            elif key == "session":
                section = "session"
                cfg.setdefault("session", {})
            else:
                section = None
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if section == "paths":
            cfg["paths"][k] = v
        elif section == "session":
            if v.lower() in ("true", "false"):
                cfg.setdefault("session", {})[k] = v.lower() == "true"
            else:
                cfg.setdefault("session", {})[k] = v
        else:
            if v.lower() in ("true", "false"):
                cfg[k] = v.lower() == "true"
            else:
                try:
                    cfg[k] = float(v) if "." in v else int(v)
                except ValueError:
                    cfg[k] = v
    return cfg


def p(path_key: str, cfg: dict) -> Path:
    return REPO / cfg["paths"][path_key]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def kill_on(cfg: dict) -> bool:
    f = p("kill_switch", cfg)
    if not f.exists():
        return False
    return f.read_text().strip().upper().startswith("ON")


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text() or json.dumps(default))
    except Exception:
        return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")


def fetch_klines(symbol: str, interval: str, limit: int = 300) -> list:
    url = (
        f"https://data-api.binance.vision/api/v3/klines"
        f"?symbol={symbol}&interval={interval}&limit={limit}"
    )
    req = Request(url, headers={"User-Agent": "sol-day-runner/1.0"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fetch_price(symbol: str) -> float:
    url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}"
    req = Request(url, headers={"User-Agent": "sol-day-runner/1.0"})
    with urlopen(req, timeout=15) as r:
        return float(json.loads(r.read().decode())["price"])


def calc_atr(high, low, close, period=14):
    tr = np.maximum(
        high[1:] - low[1:],
        np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])),
    )
    atr = np.full(len(close), np.nan)
    if len(tr) < period:
        return atr
    atr[period] = np.mean(tr[:period])
    for i in range(period + 1, len(close)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i - 1]) / period
    return atr


def find_swings(high, low, left=2, right=2):
    sh, sl = [], []
    for i in range(left, len(high) - right):
        if all(high[i] >= high[j] for j in range(i - left, i + right + 1) if j != i):
            sh.append((i, float(high[i])))
        if all(low[i] <= low[j] for j in range(i - left, i + right + 1) if j != i):
            sl.append((i, float(low[i])))
    return sh, sl


def detect_setup(klines, fvg_min_mult: float) -> dict | None:
    highs = np.array([float(c[2]) for c in klines])
    lows = np.array([float(c[3]) for c in klines])
    closes = np.array([float(c[4]) for c in klines])
    atr = calc_atr(highs, lows, closes)
    swing_highs, swing_lows = find_swings(highs, lows)

    fvgs = []
    for i in range(2, len(closes)):
        if highs[i - 2] < lows[i]:
            fvgs.append(
                {
                    "idx": i,
                    "type": "bull",
                    "top": float(lows[i]),
                    "bot": float(highs[i - 2]),
                    "size": float(lows[i] - highs[i - 2]),
                }
            )
        if lows[i - 2] > highs[i]:
            fvgs.append(
                {
                    "idx": i,
                    "type": "bear",
                    "top": float(lows[i - 2]),
                    "bot": float(highs[i]),
                    "size": float(lows[i - 2] - highs[i]),
                }
            )

    recent_sh, recent_sl = [], []
    last_choch_bull = last_choch_bear = -999
    candidates = []

    start = max(30, len(closes) - 80)
    for i in range(start, len(closes)):
        for sh_idx, sh_p in swing_highs:
            if sh_idx == i:
                recent_sh.append((i, sh_p))
                if len(recent_sh) > 5:
                    recent_sh.pop(0)
        for sl_idx, sl_p in swing_lows:
            if sl_idx == i:
                recent_sl.append((i, sl_p))
                if len(recent_sl) > 5:
                    recent_sl.pop(0)

        if len(recent_sh) >= 2:
            last_sh_idx, last_sh_p = recent_sh[-1]
            if i > last_sh_idx and closes[i] > last_sh_p and last_choch_bull < last_sh_idx:
                if recent_sh[-1][1] < recent_sh[-2][1]:
                    last_choch_bull = i
                    for f in fvgs:
                        if last_choch_bull < f["idx"] <= last_choch_bull + 10 and f["type"] == "bull":
                            a = atr[f["idx"]] if not np.isnan(atr[f["idx"]]) else 0.5
                            if f["size"] < fvg_min_mult * a:
                                continue
                            filled = False
                            for j in range(f["idx"] + 1, min(f["idx"] + 20, len(closes))):
                                if lows[j] <= f["top"] and highs[j] >= f["bot"]:
                                    filled = True
                                    break
                            if not filled and lows[-1] <= f["top"] * 1.002 and highs[-1] >= f["bot"] * 0.998:
                                filled = True
                            if not filled:
                                continue
                            entry = (f["top"] + f["bot"]) / 2
                            stop = f["bot"] - 0.15 * a
                            risk = entry - stop
                            if risk < 0.05:
                                continue
                            candidates.append(
                                {
                                    "direction": "long",
                                    "entry": entry,
                                    "stop": stop,
                                    "fvg_top": f["top"],
                                    "fvg_bot": f["bot"],
                                    "atr": float(a),
                                    "choch_idx": last_choch_bull,
                                    "fvg_idx": f["idx"],
                                    "target_3r": entry + 3 * risk,
                                    "target_4r": entry + 4 * risk,
                                    "risk": risk,
                                }
                            )
                            break

        if len(recent_sl) >= 2:
            last_sl_idx, last_sl_p = recent_sl[-1]
            if i > last_sl_idx and closes[i] < last_sl_p and last_choch_bear < last_sl_idx:
                if recent_sl[-1][1] > recent_sl[-2][1]:
                    last_choch_bear = i
                    for f in fvgs:
                        if last_choch_bear < f["idx"] <= last_choch_bear + 10 and f["type"] == "bear":
                            a = atr[f["idx"]] if not np.isnan(atr[f["idx"]]) else 0.5
                            if f["size"] < fvg_min_mult * a:
                                continue
                            filled = False
                            for j in range(f["idx"] + 1, min(f["idx"] + 20, len(closes))):
                                if highs[j] >= f["bot"] and lows[j] <= f["top"]:
                                    filled = True
                                    break
                            if not filled and highs[-1] >= f["bot"] * 0.998 and lows[-1] <= f["top"] * 1.002:
                                filled = True
                            if not filled:
                                continue
                            entry = (f["top"] + f["bot"]) / 2
                            stop = f["top"] + 0.15 * a
                            risk = stop - entry
                            if risk < 0.05:
                                continue
                            candidates.append(
                                {
                                    "direction": "short",
                                    "entry": entry,
                                    "stop": stop,
                                    "fvg_top": f["top"],
                                    "fvg_bot": f["bot"],
                                    "atr": float(a),
                                    "choch_idx": last_choch_bear,
                                    "fvg_idx": f["idx"],
                                    "target_3r": entry - 3 * risk,
                                    "target_4r": entry - 4 * risk,
                                    "risk": risk,
                                }
                            )
                            break

    if not candidates:
        return None
    candidates.sort(key=lambda x: x["fvg_idx"], reverse=True)
    return candidates[0]


def write_signal(cfg: dict, setup: dict | None) -> dict:
    risk_usd = min(
        cfg["equity_unit_usd"] * cfg["kelly_fraction"],
        cfg["equity_unit_usd"] * cfg["max_risk_pct"],
    )
    if setup is None:
        sig = {
            "status": "WAIT",
            "ts_utc": now_iso(),
            "symbol": cfg["symbol"],
            "formula_version": "v3",
            "direction": None,
            "entry_zone": None,
            "stop": None,
            "target_3r": None,
            "target_4r": None,
            "atr_14": None,
            "risk_usd_quarter_kelly": round(risk_usd, 2),
            "equity_unit_usd": cfg["equity_unit_usd"],
            "notes": "Autonomous runner: no qualifying setup",
        }
    else:
        sig = {
            "status": "READY",
            "ts_utc": now_iso(),
            "symbol": cfg["symbol"],
            "formula_version": "v3",
            "direction": setup["direction"],
            "entry_zone": {
                "low": round(setup["fvg_bot"], 4),
                "high": round(setup["fvg_top"], 4),
                "mid": round(setup["entry"], 4),
            },
            "stop": round(setup["stop"], 4),
            "target_3r": round(setup["target_3r"], 4),
            "target_4r": round(setup["target_4r"], 4),
            "atr_14": round(setup["atr"], 4),
            "risk_usd_quarter_kelly": round(risk_usd, 2),
            "equity_unit_usd": cfg["equity_unit_usd"],
            "notes": "Autonomous runner READY",
        }
    save_json(p("latest_signal", cfg), sig)
    return sig


def daily_state(cfg: dict) -> dict:
    path = p("daily_state", cfg)
    state = load_json(path, {})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("date") != today:
        state = {"date": today, "realized_pnl_usd": 0.0, "halted": False}
        save_json(path, state)
    return state


def save_daily(cfg: dict, state: dict) -> None:
    save_json(p("daily_state", cfg), state)


def pnl_r(trade: dict, price: float) -> float:
    entry, r = trade["entry_px"], trade["r_value"]
    if trade["direction"] == "long":
        return (price - entry) / r
    return (entry - price) / r


def manage_open(cfg: dict, price: float) -> None:
    open_path = p("open_trades", cfg)
    trades = load_json(open_path, [])
    if not trades:
        return
    still = []
    for t in trades:
        ur = pnl_r(t, price)
        t["unrealized_r"] = round(ur, 3)
        t["mae_r"] = round(min(t.get("mae_r", 0.0), ur), 3)
        t["mfe_r"] = round(max(t.get("mfe_r", 0.0), ur), 3)
        t["updated_at"] = now_iso()

        hit_stop = (t["direction"] == "long" and price <= t["stop_px"]) or (
            t["direction"] == "short" and price >= t["stop_px"]
        )
        hit_tp4 = (t["direction"] == "long" and price >= t["tp4_px"]) or (
            t["direction"] == "short" and price <= t["tp4_px"]
        )
        hit_tp3 = (t["direction"] == "long" and price >= t["tp3_px"]) or (
            t["direction"] == "short" and price <= t["tp3_px"]
        )

        if hit_stop:
            close_trade(cfg, t, price, "stop_1R", -1.0)
        elif hit_tp4:
            close_trade(cfg, t, price, "tp4", 4.0)
        elif hit_tp3:
            close_trade(cfg, t, price, "tp3", 3.0)
        else:
            still.append(t)
            print(f"  OPEN {t['id'][:8]} {t['direction']} unreal={ur:.2f}R mode={t.get('mode', 'paper')}")
    save_json(open_path, still)


def close_trade(cfg: dict, trade: dict, price: float, reason: str, pr: float) -> None:
    trade["status"] = "STOPPED" if reason == "stop_1R" else "CLOSED"
    trade["exit_ts"] = now_iso()
    trade["exit_px"] = round(price, 4)
    trade["exit_reason"] = reason
    trade["pnl_r"] = round(pr, 3)
    trade["pnl_usd"] = round(pr * trade["risk_usd"], 2)
    trade["updated_at"] = now_iso()
    append_jsonl(p("closed_trades", cfg), trade)
    state = daily_state(cfg)
    state["realized_pnl_usd"] = round(state.get("realized_pnl_usd", 0.0) + trade["pnl_usd"], 2)
    limit = -cfg["equity_unit_usd"] * cfg["daily_loss_limit_pct"]
    if state["realized_pnl_usd"] <= limit:
        state["halted"] = True
        print(f"  !! Daily loss limit hit ({state['realized_pnl_usd']}). Halting new entries.")
    save_daily(cfg, state)
    print(f"  CLOSED {trade['id'][:8]} {reason} pnl={trade['pnl_r']}R (${trade['pnl_usd']})")


def try_open(cfg: dict, sig: dict, price: float) -> None:
    global LIVE_MODE
    if kill_on(cfg):
        print("  Kill switch ON — no new entries")
        return
    state = daily_state(cfg)
    if state.get("halted"):
        print("  Daily halt active — no new entries")
        return
    open_path = p("open_trades", cfg)
    if load_json(open_path, []):
        return
    if (sig.get("status") or "").upper() != "READY":
        return
    direction = sig.get("direction")
    zone = sig.get("entry_zone") or {}
    entry = zone.get("mid")
    stop = sig.get("stop")
    if entry is None or stop is None or direction not in ("long", "short"):
        return

    entry, stop = float(entry), float(stop)
    r_value = abs(entry - stop)
    if r_value <= 0:
        return
    risk_usd = float(sig.get("risk_usd_quarter_kelly") or cfg["equity_unit_usd"] * cfg["kelly_fraction"])
    size_sol = risk_usd / r_value

    if direction == "long":
        tp3, tp4 = entry + 3 * r_value, entry + 4 * r_value
    else:
        tp3, tp4 = entry - 3 * r_value, entry - 4 * r_value

    live_meta = None
    mode = "paper"
    if LIVE_MODE:
        try:
            from execution.live_executor import place_entry_with_stop

            live_meta = place_entry_with_stop(
                symbol=cfg["symbol"],
                direction=direction,
                entry=entry,
                stop=stop,
                risk_usd=risk_usd,
                live=True,
            )
            mode = "live"
            if live_meta.get("qty"):
                size_sol = float(live_meta["qty"])
            print(f"  ★ LIVE orders placed env={live_meta.get('env')} qty={size_sol}")
            if live_meta.get("stop_error"):
                print(f"  ! stop order warning: {live_meta['stop_error']}")
        except Exception as e:
            print(f"  LIVE order failed — falling back to paper only: {e}")
            live_meta = {"error": str(e)}
            mode = "paper"

    trade = {
        "id": str(uuid.uuid4()),
        "status": "OPEN",
        "mode": mode,
        "direction": direction,
        "formula_version": "v3",
        "entry_ts": now_iso(),
        "exit_ts": None,
        "entry_px": round(entry, 4),
        "exit_px": None,
        "stop_px": round(stop, 4),
        "tp3_px": round(tp3, 4),
        "tp4_px": round(tp4, 4),
        "r_value": round(r_value, 6),
        "size_sol": round(size_sol, 4),
        "risk_usd": round(risk_usd, 2),
        "equity_unit_usd": cfg["equity_unit_usd"],
        "pnl_r": None,
        "pnl_usd": None,
        "mae_r": 0.0,
        "mfe_r": 0.0,
        "unrealized_r": 0.0,
        "exit_reason": None,
        "signal_ts": sig.get("ts_utc"),
        "notes": f"autonomous_{mode}",
        "live_meta": live_meta,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "mark_price_at_open": price,
    }
    save_json(open_path, [trade])
    print(f"  ★ OPENED {mode} {direction} entry={entry} stop={stop} size={size_sol:.4f} SOL risk=${risk_usd}")


def loop_once(cfg: dict) -> None:
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] cycle live={LIVE_MODE}")
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

        manage_open(cfg, price)

        setup = detect_setup(klines, float(cfg.get("fvg_min_atr_multiple", 0.6)))
        sig = write_signal(cfg, setup)
        print(f"  signal={sig['status']} dir={sig.get('direction')}")

        try_open(cfg, sig, price)
    except URLError as e:
        print(f"  network error: {e}")
    except Exception as e:
        print(f"  error: {e}")


def main() -> None:
    global LIVE_MODE
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
    LIVE_MODE = bool(args.live)
    if LIVE_MODE and os.environ.get("BINANCE_LIVE", "0") != "1":
        print("ERROR: --live requires BINANCE_LIVE=1 in environment / .env")
        sys.exit(1)

    cfg = load_cfg()
    poll = args.poll or int(cfg.get("poll_seconds", 120))
    print("SOL Day autonomous runner")
    print(f"  mode={'LIVE' if LIVE_MODE else 'PAPER'} poll={poll}s unit=${cfg['equity_unit_usd']}")
    print(f"  kill_switch={p('kill_switch', cfg)}")
    if LIVE_MODE:
        print(f"  BINANCE_ENV={os.environ.get('BINANCE_ENV', 'testnet')}")

    while True:
        loop_once(cfg)
        if args.once:
            break
        time.sleep(poll)


if __name__ == "__main__":
    main()
