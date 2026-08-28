#!/usr/bin/env python3
"""SOL command board — two $2,000 paper books, matching columns."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import streamlit as st

REPO = Path(__file__).resolve().parents[1]
BOOK = 2000.0
SESSION_HOURS = (7, 10, 11, 20)
RSI_LONG, RSI_SHORT = 20.0, 80.0

P_STATE = REPO / "data" / "sol_1m_rsi_core_state.json"
P_TRADES = REPO / "data" / "sol_1m_rsi_core_paper_trades.jsonl"
P_KILL = REPO / "data" / "KILL_SWITCH.txt"
P_DAY_SIG = REPO / "data" / "sol_day_latest_signal.json"
P_DAY_OPEN = REPO / "data" / "sol_day_open_trades.json"
P_DAY_TRADES = REPO / "data" / "sol_day_paper_trades.jsonl"
P_DAY_DAILY = REPO / "data" / "sol_day_daily_state.json"
P_DAY_CFG = REPO / "backtest" / "config" / "sol_day_runtime.yaml"

st.set_page_config(page_title="SOL Command Board", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: "IBM Plex Sans", sans-serif; }
.stApp { background: radial-gradient(1100px 480px at 8% -12%, rgba(46,204,113,.08), transparent 52%), radial-gradient(900px 420px at 100% 0%, rgba(88,101,242,.10), transparent 46%), #0b0d12; color: #e8edf5; }
.block-container { padding-top: 1.15rem; padding-bottom: 2rem; max-width: 1360px; }
#MainMenu, footer, header { visibility: hidden; }
.kicker { font-family: "IBM Plex Mono", monospace; font-size: 11px; letter-spacing: .18em; text-transform: uppercase; color: #7d8aa3; }
h1.dash-title { font-size: 2rem; font-weight: 700; letter-spacing: -.03em; margin: .15rem 0 .35rem; color: #f4f7fb; }
.sub { color: #93a0b5; font-size: .92rem; }
.pill { font-family: "IBM Plex Mono", monospace; font-size: 12px; padding: 7px 10px; border-radius: 999px; border: 1px solid #243044; background: #121722; color: #c9d4e5; }
.pill.on { border-color: #1f6b45; background: #10261b; color: #3ee08f; }
.pill.off { border-color: #5a2430; background: #241016; color: #ff7b8a; }
.pill.closed { border-color: #3a4558; color: #9aa8bd; }
.panel { background: linear-gradient(180deg,#151a24,#10141c); border: 1px solid #232a38; border-radius: 16px; padding: 16px; margin-bottom: 14px; }
.panel h3 { margin: 0 0 12px; font-size: 1.05rem; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
.cell { background: #121722; border: 1px solid #232a38; border-radius: 12px; padding: 10px 12px; }
.lbl { font-family: "IBM Plex Mono", monospace; font-size: 10px; letter-spacing: .12em; text-transform: uppercase; color: #7d8aa3; }
.val { font-size: 1.28rem; font-weight: 650; letter-spacing: -.03em; margin-top: 4px; font-variant-numeric: tabular-nums; }
.delta { font-size: .78rem; color: #8b97ab; margin-top: 2px; }
.up { color: #3ee08f; } .down { color: #ff6b7d; }
.gate { display: flex; justify-content: space-between; gap: 10px; padding: 8px 10px; border-radius: 10px; border: 1px solid #232a38; background: #121722; margin: 6px 0; font-size: .9rem; }
.gate.ok { border-color: #1f6b45; background: #10261b; }
.need { border-radius: 12px; padding: 11px 12px; margin-top: 10px; background: #121722; border: 1px solid #2a3344; color: #d5deec; font-size: .92rem; }
.foot { margin-top: 16px; color: #6d7a90; font-family: "IBM Plex Mono", monospace; font-size: 11px; }
</style>
""",
    unsafe_allow_html=True,
)


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text() or json.dumps(default))
    except Exception:
        return default


def load_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return pd.DataFrame(rows)


def http_get(path: str):
    for base in (
        "https://data-api.binance.vision/api/v3",
        "https://api.binance.us/api/v3",
        "https://api.binance.com/api/v3",
    ):
        try:
            req = Request(f"{base}{path}", headers={"User-Agent": "sol-desk/1.2"})
            with urlopen(req, timeout=8) as r:
                return json.loads(r.read().decode())
        except Exception:
            continue
    return None


def wilder_rsi(closes: np.ndarray, period: int = 14):
    if len(closes) < period + 1:
        return None
    delta = np.diff(closes)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for i in range(period, len(delta)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def next_session(now: datetime) -> str:
    for h in SESSION_HOURS:
        if now.hour < h:
            mins = (h - now.hour) * 60 - now.minute
            return f"opens {h:02d}:00 UTC · {mins}m"
    return "next 07:00 UTC"


def gate_row(ok: bool, name: str, detail: str) -> str:
    cls = "ok" if ok else ""
    mark = "READY" if ok else "NEED"
    return f'<div class="gate {cls}"><span>{name}<br><span class="delta">{detail}</span></span><b>{mark}</b></div>'


def trade_stats(df: pd.DataFrame, r_col: str):
    if df.empty or r_col not in df.columns:
        return 0, 0, 0, 0.0
    r = pd.to_numeric(df[r_col], errors="coerce").dropna()
    wins = int((r > 0).sum())
    losses = int((r < 0).sum())
    return len(r), wins, losses, float(r.sum()) if len(r) else 0.0


def load_day_cfg() -> dict:
    out = {"equity_unit_usd": BOOK, "kelly_fraction": 0.045}
    if not P_DAY_CFG.exists():
        return out
    for line in P_DAY_CFG.read_text().splitlines():
        s = line.split("#", 1)[0].strip()
        if s.startswith("equity_unit_usd:"):
            out["equity_unit_usd"] = float(s.split(":", 1)[1].strip())
        elif s.startswith("kelly_fraction:"):
            out["kelly_fraction"] = float(s.split(":", 1)[1].strip())
    return out


now = datetime.now(timezone.utc)
sess = now.hour in SESSION_HOURS
kill = P_KILL.exists() and P_KILL.read_text().strip().upper().startswith("ON")
day_cfg = load_day_cfg()
day_book = float(day_cfg.get("equity_unit_usd") or BOOK)
kelly = float(day_cfg.get("kelly_fraction") or 0.045)
day_risk = day_book * kelly

ticker = http_get("/ticker/price?symbol=SOLUSDT") or {}
px = float(ticker["price"]) if ticker.get("price") else None
kl = http_get("/klines?symbol=SOLUSDT&interval=1m&limit=80") or []
closes = np.array([float(c[4]) for c in kl[:-1]]) if len(kl) > 2 else np.array([])
rsi = wilder_rsi(closes) if len(closes) else None

state = load_json(P_STATE, {})
trades_1m = load_jsonl(P_TRADES)
eq_1m = float(state.get("equity") or BOOK)
day_r_1m = float(state.get("day_r") or 0.0)
pos_1m = state.get("position")
n1, w1, l1, r1 = trade_stats(trades_1m, "r")
pnl_1m = eq_1m - BOOK
risk_1m = eq_1m * 0.01

sig = load_json(P_DAY_SIG, {})
day_open = load_json(P_DAY_OPEN, [])
if isinstance(day_open, dict):
    day_open = [day_open] if day_open else []
day_trades = load_jsonl(P_DAY_TRADES)
day_daily = load_json(P_DAY_DAILY, {})
closed_pnl = 0.0
if not day_trades.empty and "pnl_usd" in day_trades.columns:
    closed_pnl = float(pd.to_numeric(day_trades["pnl_usd"], errors="coerce").fillna(0).sum())
eq_15 = day_book + closed_pnl
day_pnl_15 = float(day_daily.get("realized_pnl_usd") or 0.0)
n2, w2, l2, r2 = trade_stats(day_trades, "pnl_r")
open_n = len(day_open)
halted = bool(day_daily.get("halted"))
status = str(sig.get("status") or "WAIT").upper()
notes = str(sig.get("notes") or "No latest 15m signal file yet.")
direction = sig.get("direction") or "none"
ready = status == "READY"
structure_ok = any(x in notes.lower() for x in ("bullish", "bearish", "structure"))
choch_ok = "choch" in notes.lower()
fvg_exists = "fvg" in notes.lower()
fill_ok = ready
if any(x in notes.lower() for x in ("no retrace", "no realistic fill", "still above", "no qualifying")):
    fill_ok = False

st.markdown(
    f"""
<div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin-bottom:16px;flex-wrap:wrap;">
  <div>
    <div class="kicker">Two paper books · $2,000 each · formulas locked</div>
    <h1 class="dash-title">Command board</h1>
    <div class="sub">Left 1m RSI-S · 1% risk. Right 15m SOL Day v3 · 4.5% Quarter-Kelly. Same kill file.</div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <div class="{'pill on' if sess else 'pill closed'}">{'1M OPEN' if sess else '1M CLOSED'}</div>
    <div class="{'pill off' if kill else 'pill on'}">{'KILL ON' if kill else 'KILL OFF'}</div>
    <div class="pill">{now.strftime('%H:%M:%S')} UTC</div>
    <div class="pill">{f'${px:.2f}' if px else '—'}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns(2)
pnl_cls_1 = "up" if pnl_1m >= 0 else "down"
pnl_cls_2 = "up" if (eq_15 - day_book) >= 0 else "down"

with left:
    rsi_txt = f"{rsi:.1f}" if rsi is not None else "—"
    long_ok = rsi is not None and rsi <= RSI_LONG
    short_ok = rsi is not None and rsi >= RSI_SHORT
    if rsi is None:
        now_txt = "Waiting on closed 1m bars for RSI."
    elif long_ok or short_ok:
        now_txt = f"RSI {rsi_txt} is in zone. Session still required."
    else:
        now_txt = f"Need closed RSI ≤20 or ≥80 (now {rsi_txt})."
    next_1 = (
        f"Clock is the blocker. {next_session(now)}. Formula does not enter off-hours."
        if not sess
        else "Session open. Enter on the next closed 1m bar that prints ≤20 or ≥80."
    )
    if kill:
        next_1 = "Kill switch ON. No entries on either desk."
    st.markdown(
        f"""
<div class="panel">
  <h3>1m RSI-S CORE</h3>
  <div class="grid2">
    <div class="cell"><div class="lbl">Paper account</div><div class="val">${eq_1m:,.2f}</div><div class="delta {pnl_cls_1}">start $2,000 · {pnl_1m:+.2f}</div></div>
    <div class="cell"><div class="lbl">Risk / trade</div><div class="val">${risk_1m:,.2f}</div><div class="delta">1.0% of current equity</div></div>
    <div class="cell"><div class="lbl">Day R</div><div class="val">{day_r_1m:+.2f}R</div><div class="delta">cap −3.0R · UTC date</div></div>
    <div class="cell"><div class="lbl">Inventory</div><div class="val">{'IN' if pos_1m else 'FLAT'}</div><div class="delta">{pos_1m.get('side') if pos_1m else 'no working order'}</div></div>
    <div class="cell"><div class="lbl">Closed trades</div><div class="val">{n1}</div><div class="delta">{w1}W / {l1}L · {r1:+.2f}R</div></div>
    <div class="cell"><div class="lbl">Live RSI</div><div class="val">{rsi_txt}</div><div class="delta">long ≤20 · short ≥80</div></div>
  </div>
  {gate_row(sess, "Session hour", "07 / 10 / 11 / 20 UTC · " + (next_session(now) if not sess else "inside window"))}
  {gate_row(long_ok or short_ok, "RSI extreme", f"Wilder 14 closed 1m · now {rsi_txt}")}
  {gate_row(pos_1m is None, "One trade at a time", "flat" if pos_1m is None else "already in")}
  {gate_row(not kill, "Kill switch", "OFF" if not kill else "ON")}
  {gate_row(day_r_1m > -3.0, "Daily cap", f"{day_r_1m:+.2f}R vs −3.0R")}
  <div class="need"><b>Now:</b> {now_txt}<br><b>Do next:</b> {next_1}</div>
</div>
""",
        unsafe_allow_html=True,
    )

with right:
    next_2 = "Need structure + ChoCh + first FVG ≥ 0.6×ATR, then a retrace into the gap."
    if ready:
        next_2 = f"READY {direction}. Fill FVG mid, 1R stop, 3R/4R, risk ${day_risk:.0f}."
    elif "no qualifying" in notes.lower():
        next_2 = "No qualifying 15m setup on the last detect cycle. Wait for ChoCh + first FVG."
    if fill_ok is False and choch_ok and fvg_exists:
        next_2 = "Setup exists. Do not chase. Wait for the FVG fill."
    if kill:
        next_2 = "Kill switch ON. No entries on either desk."
    if halted:
        next_2 = "15m daily loss halt is on until the Chicago date rolls."
    st.markdown(
        f"""
<div class="panel">
  <h3>15m SOL Day v3</h3>
  <div class="grid2">
    <div class="cell"><div class="lbl">Paper account</div><div class="val">${eq_15:,.2f}</div><div class="delta {pnl_cls_2}">start $2,000 · {eq_15-day_book:+.2f}</div></div>
    <div class="cell"><div class="lbl">Risk / trade</div><div class="val">${day_risk:,.2f}</div><div class="delta">4.5% Quarter-Kelly of $2,000</div></div>
    <div class="cell"><div class="lbl">Day P&amp;L</div><div class="val">${day_pnl_15:,.2f}</div><div class="delta">halt −$160 · Chicago date</div></div>
    <div class="cell"><div class="lbl">Inventory</div><div class="val">{'IN' if open_n else 'FLAT'}</div><div class="delta">{open_n} working · dir {direction}</div></div>
    <div class="cell"><div class="lbl">Closed trades</div><div class="val">{n2}</div><div class="delta">{w2}W / {l2}L · {r2:+.2f}R</div></div>
    <div class="cell"><div class="lbl">Signal</div><div class="val">{status}</div><div class="delta">formula v3 locked</div></div>
  </div>
  {gate_row(structure_ok, "Structure bias", "HH/HL or LH/LL match direction")}
  {gate_row(choch_ok, "ChoCh same way", "Change of character in that bias")}
  {gate_row(fvg_exists, "First FVG after ChoCh", "≥ 0.6 × ATR(14) on 15m")}
  {gate_row(fill_ok, "Retrace / fill", "mid or favorable edge — no chase")}
  {gate_row(open_n == 0, "One trade at a time", "flat" if open_n == 0 else f"{open_n} open")}
  {gate_row(not halted and not kill, "Risk halt", "daily halt OFF and kill OFF")}
  <div class="need"><b>Now:</b> {notes}<br><b>Do next:</b> {next_2}</div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("#### Paper logs")
c1, c2 = st.columns(2)
with c1:
    st.caption("1m RSI-S")
    if trades_1m.empty:
        st.write("No closes.")
    else:
        cols = [c for c in ["ts", "side", "r", "entry", "exit", "reason", "equity"] if c in trades_1m.columns]
        st.dataframe(trades_1m[cols] if cols else trades_1m, use_container_width=True, hide_index=True)
with c2:
    st.caption("15m SOL Day")
    if day_trades.empty:
        st.write("No closes.")
    else:
        cols = [c for c in ["exit_ts", "direction", "pnl_r", "pnl_usd", "entry_px", "exit_px", "exit_reason"] if c in day_trades.columns]
        st.dataframe(day_trades[cols] if cols else day_trades, use_container_width=True, hide_index=True)

st.markdown(
    '<div class="foot">Sizing only changed. 1m still 1% / 2R / hours 7-10-11-20. 15m still ChoCh+FVG / 3R-4R / 4.5% Kelly. Restart the 15m runner after pull so it reads unit=$2000.</div>',
    unsafe_allow_html=True,
)
