#!/usr/bin/env python3
"""SOL 1m RSI-S CORE — paper dashboard."""

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

st.set_page_config(
    page_title="SOL 1m RSI-S",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: "IBM Plex Sans", sans-serif; }

.stApp {
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(46, 204, 113, 0.08), transparent 50%),
    radial-gradient(900px 400px at 100% 0%, rgba(88, 101, 242, 0.10), transparent 45%),
    #0b0d12;
  color: #e8edf5;
}

.block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1280px; }
#MainMenu, footer, header { visibility: hidden; }

.hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 18px;
}
.kicker {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #7d8aa3;
  margin-bottom: 6px;
}
h1.dash-title {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0;
  color: #f4f7fb;
}
.sub { color: #93a0b5; font-size: 0.92rem; margin-top: 4px; }

.pill {
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  padding: 7px 10px;
  border-radius: 999px;
  border: 1px solid #243044;
  background: #121722;
  color: #c9d4e5;
  white-space: nowrap;
}
.pill.on { border-color: #1f6b45; background: #10261b; color: #3ee08f; }
.pill.off { border-color: #5a2430; background: #241016; color: #ff7b8a; }
.pill.closed { border-color: #3a4558; color: #9aa8bd; }

.card-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 8px 0 18px; }
@media (max-width: 980px) { .card-row { grid-template-columns: repeat(2, 1fr); } }

.card {
  background: linear-gradient(180deg, #151a24 0%, #10141c 100%);
  border: 1px solid #232a38;
  border-radius: 16px;
  padding: 16px 16px 14px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.18);
}
.card .lbl {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #7d8aa3;
}
.card .val {
  font-size: 1.55rem;
  font-weight: 650;
  margin-top: 8px;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}
.card .delta { font-size: 0.82rem; margin-top: 4px; color: #8b97ab; }
.up { color: #3ee08f; }
.down { color: #ff6b7d; }

.banner {
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 18px;
  border: 1px solid #232a38;
  background: #121722;
  color: #c5d0e0;
}
.banner.open {
  border-color: #2a5a3a;
  background: linear-gradient(90deg, #10261b, #121722);
  color: #b7f0cf;
}

.stat-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin: 6px 0 16px; }
@media (max-width: 980px) { .stat-row { grid-template-columns: repeat(3, 1fr); } }
.stat {
  background: #121722;
  border: 1px solid #232a38;
  border-radius: 12px;
  padding: 12px;
}
.stat .lbl { font-size: 11px; color: #7d8aa3; letter-spacing: 0.08em; text-transform: uppercase; }
.stat .val { font-size: 1.15rem; font-weight: 600; margin-top: 4px; }

div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

.foot {
  margin-top: 22px;
  color: #6d7a90;
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
}
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
        df["r"] = pd.to_numeric(df["r"], errors="coerce")
        df["result"] = df["r"].apply(
            lambda x: "WIN" if pd.notna(x) and x > 0 else ("LOSS" if pd.notna(x) and x < 0 else "FLAT")
        )
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


def next_session(now: datetime) -> str:
    hour = now.hour
    for h in SESSION_HOURS:
        if hour < h:
            mins = (h - hour) * 60 - now.minute
            return f"opens {h:02d}:00 UTC · {mins}m"
    return "next 07:00 UTC"


state = load_json(STATE_PATH, {})
trades = load_trades()
px = live_px()
now = datetime.now(timezone.utc)
sess = now.hour in SESSION_HOURS

equity = float(state.get("equity") or START_EQUITY)
if not state and not trades.empty:
    equity = float(trades.iloc[-1].get("equity") or START_EQUITY)
if trades.empty and not state:
    equity = START_EQUITY

day_r = float(state.get("day_r") or 0.0)
pos = state.get("position")
pnl_usd = equity - START_EQUITY
pnl_cls = "up" if pnl_usd >= 0 else "down"
day_cls = "up" if day_r > 0 else ("down" if day_r < 0 else "")
sess_pill = "pill on" if sess else "pill closed"
kill_pill = "pill off" if kill_on() else "pill on"
sess_label = "SESSION OPEN" if sess else "SESSION CLOSED"
kill_label = "KILL ON" if kill_on() else "KILL OFF"

st.markdown(
    f"""
<div class="hero">
  <div>
    <div class="kicker">Paper desk · SOLUSDT · 1m RSI-S</div>
    <h1 class="dash-title">Command board</h1>
    <div class="sub">$2,000 unit · 1% risk · 2R target · hours 07 / 10 / 11 / 20 UTC</div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;">
    <div class="{sess_pill}">{sess_label}</div>
    <div class="{kill_pill}">{kill_label}</div>
    <div class="pill">{now.strftime('%H:%M:%S')} UTC</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

px_txt = f"${px:.2f}" if px is not None else "—"
st.markdown(
    f"""
<div class="card-row">
  <div class="card">
    <div class="lbl">Account</div>
    <div class="val">${equity:,.2f}</div>
    <div class="delta {pnl_cls}">{pnl_usd:+.2f} · {pnl_usd/START_EQUITY*100:+.2f}%</div>
  </div>
  <div class="card">
    <div class="lbl">SOL last</div>
    <div class="val">{px_txt}</div>
    <div class="delta">Binance public feed</div>
  </div>
  <div class="card">
    <div class="lbl">Session</div>
    <div class="val">{'OPEN' if sess else 'CLOSED'}</div>
    <div class="delta">{next_session(now) if not sess else 'live window'}</div>
  </div>
  <div class="card">
    <div class="lbl">Day R</div>
    <div class="val {day_cls}">{day_r:+.2f}R</div>
    <div class="delta">resets 00:00 UTC</div>
  </div>
  <div class="card">
    <div class="lbl">Inventory</div>
    <div class="val">{'IN' if pos else 'FLAT'}</div>
    <div class="delta">{pos.get('side') if pos else 'no working order'}</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

if pos:
    st.markdown(
        f"""
<div class="banner open">
  <b>OPEN {pos.get('side')}</b>
  &nbsp; entry {float(pos.get('entry', 0)):.2f}
  &nbsp;·&nbsp; stop {float(pos.get('stop', 0)):.2f}
  &nbsp;·&nbsp; target {float(pos.get('tgt', 0)):.2f}
  &nbsp;·&nbsp; rsi {pos.get('rsi', '—')}
</div>
""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="banner">Flat. The 1m runner will write an open row here when RSI hits 20 / 80 inside session.</div>',
        unsafe_allow_html=True,
    )

if trades.empty:
    st.markdown("#### Trade log")
    st.caption("No closes in `data/sol_1m_rsi_core_paper_trades.jsonl` yet.")
else:
    wins = int((trades["r"] > 0).sum())
    losses = int((trades["r"] < 0).sum())
    total = len(trades)
    wr = wins / total if total else 0.0
    avg_r = float(trades["r"].mean())
    sum_r = float(trades["r"].sum())
    avg_win = float(trades.loc[trades["r"] > 0, "r"].mean()) if wins else 0.0
    avg_loss = float(trades.loc[trades["r"] < 0, "r"].mean()) if losses else 0.0

    st.markdown(
        f"""
<div class="stat-row">
  <div class="stat"><div class="lbl">Trades</div><div class="val">{total}</div></div>
  <div class="stat"><div class="lbl">Wins / Losses</div><div class="val">{wins} / {losses}</div></div>
  <div class="stat"><div class="lbl">Win rate</div><div class="val">{wr:.0%}</div></div>
  <div class="stat"><div class="lbl">Avg R</div><div class="val">{avg_r:+.2f}</div></div>
  <div class="stat"><div class="lbl">Total R</div><div class="val">{sum_r:+.2f}</div></div>
  <div class="stat"><div class="lbl">Avg W / L</div><div class="val">{avg_win:+.2f} / {avg_loss:+.2f}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    show = trades.copy()
    prefer = [c for c in ["ts", "side", "result", "r", "entry", "exit", "stop", "tgt", "reason", "equity", "day_r"] if c in show.columns]
    st.markdown("#### Trade log")
    st.dataframe(show[prefer] if prefer else show, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Equity")
        eq = show[["ts", "equity"]].dropna()
        if not eq.empty:
            eq = eq.set_index("ts")
            st.line_chart(eq, color="#3ee08f")
    with c2:
        st.markdown("#### R multiple")
        st.bar_chart(show.set_index("ts")["r"] if "ts" in show.columns else show["r"], color="#5865f2")

st.markdown(
    f'<div class="foot">state {STATE_PATH} · trades {TRADES_PATH} · refresh to pull new closes</div>',
    unsafe_allow_html=True,
)
