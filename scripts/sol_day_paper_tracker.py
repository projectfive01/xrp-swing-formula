#!/usr/bin/env python3
"""
SOL Day v3 — Paper Trading Tracker

Tracks OPEN and CLOSED paper trades under the locked formula:
  - $1000 monthly unit
  - Quarter-Kelly risk ≈ 4.5% ($45)
  - 1R stop, min 1:3 / prefer 1:4 targets

Commands:
  python scripts/sol_day_paper_tracker.py status
  python scripts/sol_day_paper_tracker.py open-from-signal [--live-url]
  python scripts/sol_day_paper_tracker.py close --id ID --price PRICE --reason stop|tp3|tp4|manual
  python scripts/sol_day_paper_tracker.py update-price --price PRICE
  python scripts/sol_day_paper_tracker.py stats
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request

REPO = Path(__file__).resolve().parents[1]
OPEN_FILE = REPO / "data" / "sol_day_open_trades.json"
CLOSED_FILE = REPO / "data" / "sol_day_paper_trades.jsonl"
LOCAL_SIGNAL = REPO / "data" / "sol_day_latest_signal.json"
RAW_SIGNAL = (
    "https://raw.githubusercontent.com/projectfive01/xrp-swing-formula/"
    "main/data/sol_day_latest_signal.json"
)

EQUITY_UNIT = 1000.0
KELLY_PCT = 0.045
FRESH_MIN = 90


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_open() -> list:
    if not OPEN_FILE.exists():
        return []
    return json.loads(OPEN_FILE.read_text() or "[]")


def save_open(trades: list) -> None:
    OPEN_FILE.write_text(json.dumps(trades, indent=2, default=str) + "\n")


def append_closed(trade: dict) -> None:
    with CLOSED_FILE.open("a") as f:
        f.write(json.dumps(trade, default=str) + "\n")


def load_closed() -> list:
    if not CLOSED_FILE.exists():
        return []
    rows = []
    for line in CLOSED_FILE.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_signal(remote: bool) -> dict:
    if remote:
        req = Request(RAW_SIGNAL, headers={"User-Agent": "sol-day-paper/1.0"})
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    if not LOCAL_SIGNAL.exists():
        raise SystemExit("No local signal file")
    return json.loads(LOCAL_SIGNAL.read_text())


def is_fresh(ts: str | None) -> bool:
    if not ts:
        return False
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - t <= timedelta(minutes=FRESH_MIN)
    except Exception:
        return False


def cmd_status(_: argparse.Namespace) -> None:
    open_trades = load_open()
    closed = load_closed()
    print(f"Open: {len(open_trades)} | Closed (all-time paper): {len(closed)}")
    for t in open_trades:
        print(
            f"  OPEN {t['id'][:8]} {t['direction']} entry={t['entry_px']} "
            f"stop={t['stop_px']} risk=${t.get('risk_usd')} "
            f"unreal_r={t.get('unrealized_r')}"
        )


def cmd_open_from_signal(args: argparse.Namespace) -> None:
    if load_open():
        print("Already have an open paper trade. One at a time.")
        return
    sig = load_signal(args.live_url)
    if (sig.get("status") or "").upper() != "READY":
        print("Signal is WAIT — no open.")
        return
    if not is_fresh(sig.get("ts_utc")):
        print("Signal READY but stale (>90m) — no open.")
        return

    direction = sig.get("direction")
    zone = sig.get("entry_zone") or {}
    entry = zone.get("mid")
    if entry is None and zone.get("low") is not None and zone.get("high") is not None:
        entry = (float(zone["low"]) + float(zone["high"])) / 2
    stop = sig.get("stop")
    if entry is None or stop is None or direction not in ("long", "short"):
        print("Signal missing entry/stop/direction.")
        return

    entry = float(entry)
    stop = float(stop)
    r_value = abs(entry - stop)
    if r_value <= 0:
        print("Invalid R (entry == stop).")
        return

    risk_usd = float(sig.get("risk_usd_quarter_kelly") or EQUITY_UNIT * KELLY_PCT)
    size_sol = risk_usd / r_value

    if direction == "long":
        tp3 = entry + 3 * r_value
        tp4 = entry + 4 * r_value
    else:
        tp3 = entry - 3 * r_value
        tp4 = entry - 4 * r_value

    trade = {
        "id": str(uuid.uuid4()),
        "status": "OPEN",
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
        "equity_unit_usd": EQUITY_UNIT,
        "pnl_r": None,
        "pnl_usd": None,
        "mae_r": 0.0,
        "mfe_r": 0.0,
        "unrealized_r": 0.0,
        "exit_reason": None,
        "signal_ts": sig.get("ts_utc"),
        "notes": "paper",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    save_open([trade])
    print("OPENED paper trade:")
    print(json.dumps(trade, indent=2))


def _pnl_r(trade: dict, price: float) -> float:
    entry = trade["entry_px"]
    r = trade["r_value"]
    if trade["direction"] == "long":
        return (price - entry) / r
    return (entry - price) / r


def cmd_update_price(args: argparse.Namespace) -> None:
    price = float(args.price)
    open_trades = load_open()
    if not open_trades:
        print("No open trade.")
        return
    still = []
    for t in open_trades:
        ur = _pnl_r(t, price)
        t["unrealized_r"] = round(ur, 3)
        t["mae_r"] = round(min(t.get("mae_r", 0.0), ur), 3)
        t["mfe_r"] = round(max(t.get("mfe_r", 0.0), ur), 3)
        t["updated_at"] = now_iso()

        # Auto-exit rules
        hit_stop = (
            (t["direction"] == "long" and price <= t["stop_px"])
            or (t["direction"] == "short" and price >= t["stop_px"])
        )
        hit_tp4 = (
            (t["direction"] == "long" and price >= t["tp4_px"])
            or (t["direction"] == "short" and price <= t["tp4_px"])
        )
        hit_tp3 = (
            (t["direction"] == "long" and price >= t["tp3_px"])
            or (t["direction"] == "short" and price <= t["tp3_px"])
        )

        if hit_stop:
            _close_trade(t, price, "stop_1R", -1.0)
        elif hit_tp4:
            _close_trade(t, price, "tp4", 4.0)
        elif hit_tp3:
            _close_trade(t, price, "tp3", 3.0)
        else:
            still.append(t)
            print(f"OPEN {t['id'][:8]} unreal={ur:.2f}R mae={t['mae_r']} mfe={t['mfe_r']}")
    save_open(still)


def _close_trade(trade: dict, price: float, reason: str, pnl_r: float) -> None:
    trade["status"] = "CLOSED" if reason != "stop_1R" else "STOPPED"
    trade["exit_ts"] = now_iso()
    trade["exit_px"] = round(price, 4)
    trade["exit_reason"] = reason
    trade["pnl_r"] = round(pnl_r, 3)
    trade["pnl_usd"] = round(pnl_r * trade["risk_usd"], 2)
    trade["updated_at"] = now_iso()
    append_closed(trade)
    print(f"CLOSED {trade['id'][:8]} reason={reason} pnl={trade['pnl_r']}R (${trade['pnl_usd']})")


def cmd_close(args: argparse.Namespace) -> None:
    price = float(args.price)
    reason = args.reason
    open_trades = load_open()
    if not open_trades:
        print("No open trade.")
        return
    still = []
    for t in open_trades:
        if args.id and not t["id"].startswith(args.id):
            still.append(t)
            continue
        if reason == "stop":
            pnl = -1.0
            rsn = "stop_1R"
        elif reason == "tp3":
            pnl = 3.0
            rsn = "tp3"
        elif reason == "tp4":
            pnl = 4.0
            rsn = "tp4"
        else:
            pnl = _pnl_r(t, price)
            rsn = "manual"
        _close_trade(t, price, rsn, pnl)
    save_open(still)


def cmd_stats(_: argparse.Namespace) -> None:
    closed = load_closed()
    if not closed:
        print("No closed paper trades yet.")
        return
    n = len(closed)
    wins = [t for t in closed if (t.get("pnl_r") or 0) > 0]
    losses = [t for t in closed if (t.get("pnl_r") or 0) <= 0]
    wr = len(wins) / n * 100
    avg_r = sum(t.get("pnl_r") or 0 for t in closed) / n
    avg_win = sum(t.get("pnl_r") or 0 for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get("pnl_r") or 0 for t in losses) / len(losses) if losses else 0
    total_usd = sum(t.get("pnl_usd") or 0 for t in closed)

    # Kelly from live paper sample
    p = len(wins) / n
    b = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    q = 1 - p
    full_kelly = ((b * p) - q) / b if b > 0 else 0
    quarter_kelly = full_kelly / 4

    print("=== SOL Day Paper Stats ===")
    print(f"Trades      : {n}")
    print(f"Win rate    : {wr:.1f}%")
    print(f"Avg R       : {avg_r:.2f}")
    print(f"Avg win R   : {avg_win:.2f}")
    print(f"Avg loss R  : {avg_loss:.2f}")
    print(f"Total P&L $ : {total_usd:.2f}")
    print(f"Full Kelly  : {full_kelly*100:.1f}%")
    print(f"Quarter Kelly (live sample): {quarter_kelly*100:.1f}%")
    print("(Recalibrate risk % after ≥30 closed trades)")


def main() -> None:
    p = argparse.ArgumentParser(description="SOL Day v3 paper tracker")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")
    op = sub.add_parser("open-from-signal")
    op.add_argument("--live-url", action="store_true")
    cl = sub.add_parser("close")
    cl.add_argument("--id", default="")
    cl.add_argument("--price", required=True)
    cl.add_argument("--reason", choices=["stop", "tp3", "tp4", "manual"], default="manual")
    up = sub.add_parser("update-price")
    up.add_argument("--price", required=True)
    sub.add_parser("stats")

    args = p.parse_args()
    {
        "status": cmd_status,
        "open-from-signal": cmd_open_from_signal,
        "close": cmd_close,
        "update-price": cmd_update_price,
        "stats": cmd_stats,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
