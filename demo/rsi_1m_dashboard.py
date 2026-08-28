#!/usr/bin/env python3
"""SOL 1m RSI-S CORE — paper dashboard.

Read-only scoreboard. Does not place trades.

  streamlit run demo/rsi_1m_dashboard.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

REPO = Path(__file__).resolve().parents[1]
STATE_PATH = REPO / "data" / "sol_1m_rsi_core_state.json"
TRADES_PATH = REPO / "data" / "sol_1m_rsi_core_paper_trades.jsonl"
KILL_PATH = REPO / "data" / "KILL_SWITCH.txt"
START_EQUITY = 2000.0
SESSION_HOURS = (7, 10, 11, 20)

st.set_page_config(page_title="SOL 1m RSI-S", page_icon="📊", layout="wide")


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text() or json.dumps(default))
    except Exception:
        return default


def load_trades() -> pd.DataFrame:
    rows = []
    if TRADES_PATH.exists():
        for line in TRADES_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame(
            columns=["ts", "side", "entry", "exit", "stop", "tgt", "r", "reason", "equity", "day_r", "result"]
        )
    df = pd.DataFrame(rows)
    if "r" in df.columns:
        df["result"] = df["r"].apply(lambda x: "WIN" if float(x) > 0 else ("LOSS" if float(x) < 0 else "FLAT"))
    return df


def live_px():
    for url in (
        "https://data-api.binance.vision/api/v3/ticker/price?symbol=SOLUSDT",
        "https://api.binance.us/api/v3/ticker/price?symbol=SOLUSDT",
    ):
        try:
            req = Request(url, headers={"User-Agent": "sol-1m-dash/1.0"})
            with urlopen(req, timeout=8) as r:
                return float(json.loads(r.read().decode())["price"])
        except Exception:
            continue
    return None


def kill_on() -> bool:
    if not KILL_PATH.exists():
        return False
    return KILL_PATH.read_text().strip().upper().startswith("ON")


state = load_json(STATE_PATH, {})
trades = load_trades()
px = live_px()
now = datetime.now(timezone.utc)
sess = now.hour in SESSION_HOURS

equity = float(state.get("equity") or START_EQUITY)
if trades.empty and not state:
    equity = START_EQUITY
elif not state and not trades.empty:
    equity = float(trades.iloc[-1].get("equity") or START_EQUITY)

day_r = float(state.get("day_r") or 0.0)
pos = state.get("position")
pnl_usd = equity - START_EQUITY
pnl_pct = (pnl_usd / START_EQUITY) * 100.0

st.title("SOL 1m RSI-S CORE")
st.caption("Paper scoreboard • $2,000 start • 1% risk • 2R target • hours 7/10/11/20 UTC")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Account", f"${equity:,.2f}", f"{pnl_usd:+.2f} ({pnl_pct:+.1f}%)")
c2.metric("SOL last", f"${px:.2f}" if px is not None else "—")
c3.metric("Session", "OPEN" if sess else "CLOSED", f"{now.strftime('%H:%M')} UTC")
c4.metric("Day R", f"{day_r:+.2f}R")
c5.metric("Kill switch", "ON" if kill_on() else "OFF")

if pos:
    st.warning(
        f"OPEN {pos.get('side')} @ {float(pos.get('entry', 0)):.2f}  "
        f"stop {float(pos.get('stop', 0)):.2f}  tgt {float(pos.get('tgt', 0)):.2f}  "
        f"rsi {pos.get('rsi', '—')}"
    )
else:
    st.info("No open 1m RSI paper position in state file.")

st.divider()

if trades.empty:
    st.subheader("Trade log")
    st.write(
        "No closed trades in `data/sol_1m_rsi_core_paper_trades.jsonl` yet. "
        "When the paper runner exits a trade it appends a row here."
    )
else:
    wins = int((trades["r"].astype(float) > 0).sum())
    losses = int((trades["r"].astype(float) < 0).sum())
    total = len(trades)
    wr = wins / total if total else 0.0
    avg_r = float(trades["r"].astype(float).mean())
    sum_r = float(trades["r"].astype(float).sum())
    avg_win = float(trades.loc[trades["r"].astype(float) > 0, "r"].astype(float).mean()) if wins else 0.0
    avg_loss = float(trades.loc[trades["r"].astype(float) < 0, "r"].astype(float).mean()) if losses else 0.0

    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Trades", total)
    s2.metric("Wins / Losses", f"{wins} / {losses}")
    s3.metric("Win rate", f"{wr:.0%}")
    s4.metric("Avg R", f"{avg_r:+.2f}")
    s5.metric("Total R", f"{sum_r:+.2f}")
    s6.metric("Avg win / loss", f"{avg_win:+.2f} / {avg_loss:+.2f}")

    st.subheader("Trade log")
    show = trades.copy()
    prefer = [c for c in ["ts", "side", "result", "r", "entry", "exit", "stop", "tgt", "reason", "equity", "day_r"] if c in show.columns]
    st.dataframe(show[prefer] if prefer else show, use_container_width=True, hide_index=True)

    st.subheader("Equity after each close")
    eq = show[["ts", "equity"]].dropna()
    if not eq.empty:
        eq = eq.set_index("ts")
        st.line_chart(eq)

    st.subheader("R multiple")
    st.bar_chart(show.set_index("ts")["r"] if "ts" in show.columns else show["r"])

st.divider()
st.caption(f"State: `{STATE_PATH}`  •  Trades: `{TRADES_PATH}`  •  Refresh the page to pull new closes.")
