#!/usr/bin/env python3
"""
SOL Day v3 — Signal Watcher (paper-first)

Polls data/sol_day_latest_signal.json (local clone or raw GitHub URL).
When status == READY and signal is fresh, logs a paper trade and prints
clear execution instructions (size via Quarter-Kelly).

Usage:
  python scripts/sol_day_signal_watcher.py
  python scripts/sol_day_signal_watcher.py --once
  python scripts/sol_day_signal_watcher.py --live-url   # poll raw GitHub

Env (optional for later live mode):
  BINANCE_API_KEY / BINANCE_API_SECRET  — only if you later enable live orders
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import urlopen, Request

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_SIGNAL = REPO_ROOT / "data" / "sol_day_latest_signal.json"
PAPER_LOG = REPO_ROOT / "data" / "sol_day_paper_trades.jsonl"
RAW_URL = (
    "https://raw.githubusercontent.com/projectfive01/xrp-swing-formula/"
    "main/data/sol_day_latest_signal.json"
)

FRESH_MINUTES = 90  # ignore READY older than this
POLL_SECONDS = 60


def load_signal(use_remote: bool) -> dict:
    if use_remote:
        req = Request(RAW_URL, headers={"User-Agent": "sol-day-watcher/1.0"})
        with urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    if not LOCAL_SIGNAL.exists():
        return {"status": "WAIT", "notes": "local signal file missing"}
    return json.loads(LOCAL_SIGNAL.read_text())


def is_fresh(ts_utc: str | None) -> bool:
    if not ts_utc:
        return False
    try:
        ts = datetime.fromisoformat(ts_utc.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - ts <= timedelta(minutes=FRESH_MINUTES)
    except Exception:
        return False


def size_from_kelly(signal: dict) -> dict:
    equity = float(signal.get("equity_unit_usd") or 1000)
    risk_pct = 0.045  # Quarter-Kelly locked
    risk_usd = float(signal.get("risk_usd_quarter_kelly") or equity * risk_pct)
    entry = None
    stop = signal.get("stop")
    zone = signal.get("entry_zone") or {}
    if zone.get("mid") is not None:
        entry = float(zone["mid"])
    elif zone.get("low") is not None and zone.get("high") is not None:
        entry = (float(zone["low"]) + float(zone["high"])) / 2
    if entry is None or stop is None:
        return {"risk_usd": risk_usd, "size_sol": None, "entry": entry, "stop": stop}
    risk_per_sol = abs(entry - float(stop))
    size_sol = risk_usd / risk_per_sol if risk_per_sol > 0 else None
    return {
        "risk_usd": round(risk_usd, 2),
        "size_sol": round(size_sol, 4) if size_sol else None,
        "entry": round(entry, 4),
        "stop": round(float(stop), 4),
        "target_3r": signal.get("target_3r"),
        "target_4r": signal.get("target_4r"),
    }


def already_logged(signal: dict) -> bool:
    if not PAPER_LOG.exists():
        return False
    key = f"{signal.get('ts_utc')}|{signal.get('direction')}|{signal.get('status')}"
    for line in PAPER_LOG.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            row_key = f"{row.get('ts_utc')}|{row.get('direction')}|{row.get('status')}"
            if row_key == key:
                return True
        except Exception:
            continue
    return False


def log_paper(signal: dict, sizing: dict) -> None:
    row = {
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        **signal,
        "paper_sizing": sizing,
        "mode": "paper",
    }
    with PAPER_LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")


def handle(signal: dict) -> None:
    status = (signal.get("status") or "WAIT").upper()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] status={status} ts={signal.get('ts_utc')}")

    if status != "READY":
        return
    if not is_fresh(signal.get("ts_utc")):
        print("  → READY but stale — ignore")
        return
    if already_logged(signal):
        print("  → already paper-logged — skip")
        return

    sizing = size_from_kelly(signal)
    log_paper(signal, sizing)

    print("  ★ PAPER ENTRY LOGGED")
    print(f"  Direction : {signal.get('direction')}")
    print(f"  Entry     : {sizing.get('entry')}")
    print(f"  Stop      : {sizing.get('stop')}")
    print(f"  Size SOL  : {sizing.get('size_sol')}")
    print(f"  Risk USD  : {sizing.get('risk_usd')} (Quarter-Kelly)")
    print(f"  Target 3R : {sizing.get('target_3r')}")
    print(f"  Target 4R : {sizing.get('target_4r')}")
    print("  (Live orders disabled by default — enable only after paper validation)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Single check then exit")
    parser.add_argument("--live-url", action="store_true", help="Poll raw GitHub instead of local file")
    args = parser.parse_args()

    while True:
        try:
            signal = load_signal(use_remote=args.live_url)
            handle(signal)
        except Exception as e:
            print(f"Error: {e}")
        if args.once:
            break
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
