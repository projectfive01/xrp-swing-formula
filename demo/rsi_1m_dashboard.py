#!/usr/bin/env python3
"""SOL command board — 1m RSI-S + 15m SOL Day."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import streamlit as st

REPO = Path(__file__).resolve().parents[1]
START_EQUITY_1M = 2000.0
SESSION_HOURS = (7, 10, 11, 20)
RSI_LONG, RSI_SHORT = 20.0, 80.0

P_STATE = REPO / "data" / "sol_1m_rsi_core_state.json"
P_TRADES = REPO / "data" / "sol_1m_rsi_core_paper_trades.jsonl"
P_KILL = REPO / "data" / "KILL_SWITCH.txt"
P_DAY_SIG = REPO / "data" / "sol_day_latest_signal.json"
P_DAY_OPEN = REPO / "data" / "sol_day_open_trades.json"
P_DAY_TRADES = REPO / "data" / "sol_day_paper_trades.jsonl"
P_DAY_DAILY = REPO / "data" / "sol_day_daily_state.json"

st.set_page_config(page_title="SOL Command Board", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family: "IBM Plex Sans", sans-serif; }
.stApp {
  background:
    radial-gradient(1100px 480px at 8% -12%, rgba(46,204,113,.08), transparent 52%),
    radial-gradient(900px 420px at 100% 0%, rgba(88,101,242,.10), transparent 46%),
    #0b0d12;
  color: #e8edf5;
}
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1320px; }
#MainMenu, footer, header { visibility: hidden; }
.kicker { font-family: "IBM Plex Mono", monospace; font-size: 11px; letter-spacing: .18em; text-transform: uppercase; color: #7d8aa3; }
h1.dash-title { font-size: 2rem; font-weight: 700; letter-spacing: -.03em; margin: .15rem 0 .35rem; color: #f4f7fb; }
.sub { color: #93a0b5; font-size: .92rem; }
.pill { font-family: "IBM Plex Mono", monospace; font-size: 12px; padding: 7px 10px; border-radius: 999px; border: 1px solid #243044; background: #121722; color: #c9d4e5; }
.pill.on { border-color: #1f6b45; background: #10261b; color: #3ee08f; }
.pill.off { border-color: #5a2430; background: #241016; color: #ff7b8a; }
.pill.closed { border-color: #3a4558; color: #9aa8bd; }
.panel { background: linear-gradient(180deg,#151a24,#10141c); border: 1px solid #232a38; border-radius: 16px; padding: 16px 16px 14px; margin-bottom: 14px; }
.panel h3 { margin: 0 0 10px; font-size: 1.05rem; }
.lbl { font-family: "IBM Plex Mono", monospace; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: #7d8aa3; }
.val { font-size: 1.45rem; font-weight: 650; letter-spacing: -.03em; margin-top: 6px; }
.delta { font-size: .82rem; color: #8b97ab; margin-top: 3px; }
.up { color: #3ee08f; } .down { color: #ff6b7d; }
.gate { display: flex; justify-content: space-between; gap: 10px; padding: 8px 10px; border-radius: 10px; border: 1px solid #232a38; background: #121722; margin: 6px 0; font-size: .92rem; }
.gate.ok { border-color: #1f6b45; background: #10261b; }
.gate.no { border-color: #3a4558; }
.need { border-radius: 12px; padding: 11px 12px; margin-top: 10px; background: #121722; border: 1px solid #2a3344; color: #d5deec; }
.foot { margin-top: 18px; color: #6d7a90; font-family: "IBM Plex Mono", monospace; font-size: 11px; }
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
            if not line.strip():
                continue
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
            req = Request(f"{base}{path}", headers={"User-Agent": "sol-desk/1.1"})
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
    cls = "ok" if ok else "no"
    mark = "READY" if ok else "NEED"
    return f'<div class="gate {cls}"><span>{name}<br><span class="delta">{detail}</span></span><b>{mark}</b></div>'


now = datetime.now(timezone.utc)
sess = now.hour in SESSION_HOURS
kill = P_KILL.exists() and P_KILL.read_text().strip().upper().startswith("ON")

ticker = http_get("/ticker/price?symbol=SOLUSDT") or {}
px = float(ticker["price"]) if ticker.get("price") else None
kl = http_get("/klines?symbol=SOLUSDT&interval=1m&limit=80") or []
closes = np.array([float(c[4]) for c in kl[:-1]]) if len(kl) > 2 else np.array([])
rsi = wilder_rsi(closes) if len(closes) else None

state = load_json(P_STATE, {})
trades_1m = load_jsonl(P_TRADES)
equity_1m = float(state.get("equity") or START_EQUITY_1M)
day_r = float(state.get("day_r") or 0.0)
pos_1m = state.get("position")

sig = load_json(P_DAY_SIG, {})
day_open = load_json(P_DAY_OPEN, [])
if isinstance(day_open, dict):
    day_open = [day_open] if day_open else []
day_trades = load_jsonl(P_DAY_TRADES)
day_daily = load_json(P_DAY_DAILY, {})

st.markdown(
    f"""
<div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-end;margin-bottom:16px;flex-wrap:wrap;">
  <div>
    <div class="kicker">SOL desk · two locked formulas</div>
    <h1 class="dash-title">Command board</h1>
    <div class="sub">1m RSI-S paper $2,000 · 15m SOL Day v3 micro unit · same kill file</div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;">
    <div class="{'pill on' if sess else 'pill closed'}">{'1M SESSION OPEN' if sess else '1M SESSION CLOSED'}</div>
    <div class="{'pill off' if kill else 'pill on'}">{'KILL ON' if kill else 'KILL OFF'}</div>
    <div class="pill">{now.strftime('%H:%M:%S')} UTC</div>
    <div class="pill">{f'${px:.2f}' if px else '—'}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns(2)

with left:
    rsi_txt = f"{rsi:.1f}" if rsi is not None else "—"
    long_ok = rsi is not None and rsi <= RSI_LONG
    short_ok = rsi is not None and rsi >= RSI_SHORT
    if rsi is None:
        rsi_need = "Waiting on 1m closes to compute RSI."
    elif long_ok:
        rsi_need = "RSI is in the long zone. Still need session open + no open trade."
    elif short_ok:
        rsi_need = "RSI is in the short zone. Still need session open + no open trade."
    elif rsi < 50:
        rsi_need = f"Need closed RSI ≤ 20 for a long (now {rsi:.1f}) or ≥ 80 for a short."
    else:
        rsi_need = f"Need closed RSI ≥ 80 for a short (now {rsi:.1f}) or ≤ 20 for a long."

    next_act = (
        "Session is the blocker. Next window is 07:00 UTC / 02:00 CDT. RSI can arm before that, but the runner will not enter."
        if not sess
        else (
            "Session is open. Wait for a closed 1m bar with RSI ≤ 20 or ≥ 80, then take 1×ATR stop / 2R target."
            if not (long_ok or short_ok)
            else "Session open and RSI is in zone. If the 1m runner is alive and flat, it should print PAPER LONG/SHORT on the next closed bar."
        )
    )
    if kill:
        next_act = "Kill switch is ON. Turn it OFF or delete data/KILL_SWITCH.txt before either formula can enter."

    st.markdown(
        f"""
<div class="panel">
  <h3>1m RSI-S CORE</h3>
  <div class="lbl">Paper account</div>
  <div class="val">${equity_1m:,.2f}</div>
  <div class="delta">day R {day_r:+.2f} · inventory {('IN ' + str(pos_1m.get('side'))) if pos_1m else 'FLAT'}</div>
  <div style="height:10px"></div>
  {gate_row(sess, "Session hour", "Locked hours 07 / 10 / 11 / 20 UTC · " + (next_session(now) if not sess else "inside window"))}
  {gate_row(long_ok or short_ok, "RSI extreme", f"Wilder 14 on closed 1m · now {rsi_txt} · long ≤20 · short ≥80")}
  {gate_row(pos_1m is None, "One trade at a time", "No working 1m paper position" if pos_1m is None else "Already in a 1m trade")}
  {gate_row(not kill, "Kill switch", "OFF" if not kill else "ON — entries blocked")}
  {gate_row(day_r > -3.0, "Daily cap", f"{day_r:+.2f}R vs −3.0R halt")}
  <div class="need"><b>Now:</b> {rsi_need}<br><b>Do next:</b> {next_act}</div>
</div>
""",
        unsafe_allow_html=True,
    )

with right:
    status = str(sig.get("status") or "WAIT").upper()
    notes = str(sig.get("notes") or "No latest signal file yet. Run the 15m autonomous runner.")
    direction = sig.get("direction") or "none"
    ready = status == "READY"
    open_n = len(day_open) if isinstance(day_open, list) else 0
    halted = bool(day_daily.get("halted"))
    unit = sig.get("equity_unit_usd") or 96
    structure_ok = "bullish" in notes.lower() or "bearish" in notes.lower() or "structure" in notes.lower()
    choch_ok = "choch" in notes.lower()
    fvg_exists = "fvg" in notes.lower()
    fill_ok = ready
    if "no retrace" in notes.lower() or "no realistic fill" in notes.lower() or "still above" in notes.lower():
        fill_ok = False
        fvg_exists = True
        choch_ok = True
        structure_ok = True

    day_next = "Need first FVG after ChoCh to get tagged / filled. Do not chase above the gap."
    if ready:
        day_next = f"READY {direction}. Enter on FVG retrace, 1R structural stop, 3R/4R targets, size off ${unit} unit."
    elif not choch_ok:
        day_next = "Wait for structure bias + ChoCh in the same direction on 15m."
    elif not fvg_exists:
        day_next = "ChoCh exists. Wait for the first FVG after it, size ≥ 0.6×ATR."
    if kill:
        day_next = "Kill switch is ON. Both desks are blocked."
    if halted:
        day_next = "Daily loss halt is on for SOL Day. No new 15m entries until the Chicago date rolls."

    st.markdown(
        f"""
<div class="panel">
  <h3>15m SOL Day v3</h3>
  <div class="lbl">Signal</div>
  <div class="val">{status}</div>
  <div class="delta">dir {direction} · unit ${unit} · open trades {open_n}</div>
  <div style="height:10px"></div>
  {gate_row(structure_ok, "Structure bias", "HH/HL or LH/LL must match trade direction")}
  {gate_row(choch_ok, "ChoCh same way", "Change of character in that bias")}
  {gate_row(fvg_exists, "First FVG after ChoCh", "Gap ≥ 0.6 × ATR(14) on 15m")}
  {gate_row(fill_ok, "Retrace / fill available", "Enter FVG mid or favorable edge — no chase")}
  {gate_row(open_n == 0, "One trade at a time", "No working 15m paper position" if open_n == 0 else f"{open_n} open")}
  {gate_row(not halted and not kill, "Risk halt", "Daily halt OFF and kill OFF")}
  <div class="need"><b>Now:</b> {notes}<br><b>Do next:</b> {day_next}</div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("#### Paper logs")
t1, t2 = st.columns(2)
with t1:
    st.caption("1m RSI-S closes")
    if trades_1m.empty:
        st.write("No 1m closes yet.")
    else:
        df = trades_1m.copy()
        if "r" in df.columns:
            df["result"] = df["r"].apply(lambda x: "WIN" if float(x) > 0 else ("LOSS" if float(x) < 0 else "FLAT"))
        cols = [c for c in ["ts", "side", "result", "r", "entry", "exit", "reason", "equity"] if c in df.columns]
        st.dataframe(df[cols] if cols else df, use_container_width=True, hide_index=True)
with t2:
    st.caption("15m SOL Day closes")
    if day_trades.empty:
        st.write("No 15m paper closes yet.")
    else:
        cols = [c for c in ["exit_ts", "direction", "status", "pnl_r", "entry_px", "exit_px", "exit_reason"] if c in day_trades.columns]
        st.dataframe(day_trades[cols] if cols else day_trades, use_container_width=True, hide_index=True)

st.markdown(
    '<div class="foot">1m hours are a hard gate. 15m session is preference only (open_only_during_session=false). Refresh for a new RSI / signal snapshot.</div>',
    unsafe_allow_html=True,
)
