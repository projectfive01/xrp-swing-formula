"""
XRP Swing + SOL Day — Feature Demo
Includes: Signal Load-Bar | Paper Trading ($2k / 1R / 3R / 5R) | Backtesting
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

st.set_page_config(
    page_title="XRP Swing Formula Demo",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------
# Shared Unit Rules
# ------------------------------------------------------------
UNIT_SIZE = 2000.0

def calculate_levels(entry: float, stop: float):
    r = abs(entry - stop)
    return {
        "r_value": r,
        "stop": stop,
        "tp1": entry + 3 * r,
        "tp2": entry + 5 * r,
        "risk_usd": UNIT_SIZE * (r / entry) if entry else 0,
    }

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
st.sidebar.title("XRP Swing Formula")
st.sidebar.markdown("**Unit Rules (Frozen)**")
st.sidebar.markdown(f"""
- Unit Size: **${UNIT_SIZE:,.0f}**
- Max Loss: **1R**
- Take Profit 1: **3R**
- Take Profit 2: **5R**
""")

page = st.sidebar.radio(
    "Navigation",
    ["Signal & Load-Bar", "Paper Trading", "Backtesting", "SOL Day (Scaffold)", "About"],
)

# ------------------------------------------------------------
# Helper: fake / sample data for demo
# ------------------------------------------------------------
@st.cache_data
def get_sample_ohlcv(n=300):
    np.random.seed(42)
    dates = pd.date_range(end=datetime.utcnow(), periods=n, freq="D")
    price = 0.6
    rows = []
    for d in dates:
        change = np.random.randn() * 0.03
        open_p = price
        close_p = price * (1 + change)
        high_p = max(open_p, close_p) * (1 + abs(np.random.randn()) * 0.01)
        low_p = min(open_p, close_p) * (1 - abs(np.random.randn()) * 0.01)
        vol = abs(np.random.randn() * 1e8)
        rows.append([d, open_p, high_p, low_p, close_p, vol])
        price = close_p
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df = df.set_index("date")
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def simple_signal(df):
    """Lightweight BASE-style signal for demo purposes."""
    df = df.copy()
    df["sma200"] = df["close"].rolling(200, min_periods=50).mean()
    df["rsi"] = compute_rsi(df["close"])
    df["rise_10d"] = df["close"] / df["close"].shift(10) - 1

    latest = df.iloc[-1]
    exhaustion = (latest["rise_10d"] >= 0.20) and (latest["rsi"] >= 75)
    holds_200 = latest["close"] >= (latest["sma200"] * 0.98) if pd.notna(latest["sma200"]) else False

    # Simple pullback proxy
    local_high = df["high"].iloc[-15:].max()
    pullback = (local_high - latest["close"]) / local_high if local_high > 0 else 0
    pullback_ok = pullback >= 0.10

    gates = {
        "exhaustion": bool(exhaustion),
        "pullback_10pct": bool(pullback_ok),
        "holds_200d": bool(holds_200),
    }
    progress = sum(gates.values()) / len(gates)
    action = "BUY" if progress == 1.0 else "HOLD"

    return {
        "action": action,
        "progress": progress,
        "gates": gates,
        "close": float(latest["close"]),
        "rsi": float(latest["rsi"]) if pd.notna(latest["rsi"]) else None,
        "sma200": float(latest["sma200"]) if pd.notna(latest["sma200"]) else None,
        "local_high": float(local_high),
        "pullback_pct": float(pullback),
    }

# ------------------------------------------------------------
# PAGE: Signal & Load-Bar
# ------------------------------------------------------------
if page == "Signal & Load-Bar":
    st.title("XRP BASE Signal")
    st.caption("Frozen BASE formula • Load-bar must reach 100% before BUY")

    df = get_sample_ohlcv()
    sig = simple_signal(df)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Action", sig["action"])
    col2.metric("Progress", f"{sig['progress']*100:.0f}%")
    col3.metric("Close", f"${sig['close']:.4f}")
    col4.metric("RSI", f"{sig['rsi']:.1f}" if sig["rsi"] else "—")

    st.subheader("Load-Bar (Gates)")
    progress = sig["progress"]
    st.progress(progress)

    gate_cols = st.columns(3)
    for i, (name, ok) in enumerate(sig["gates"].items()):
        with gate_cols[i]:
            st.markdown(f"{'✅' if ok else '⬜️'} **{name}**")

    st.subheader("Key Levels")
    st.write({
        "Local High": round(sig["local_high"], 4),
        "Pullback %": f"{sig['pullback_pct']*100:.1f}%",
        "200-SMA": round(sig["sma200"], 4) if sig["sma200"] else None,
    })

    st.line_chart(df["close"].tail(120))

# ------------------------------------------------------------
# PAGE: Paper Trading
# ------------------------------------------------------------
elif page == "Paper Trading":
    st.title("Paper Trading — $2,000 Units")
    st.markdown("**1R risk • 3R / 5R targets**")

    st.info("This demo uses simulated prices. In production the daily runner feeds real data.")

    col_a, col_b = st.columns(2)
    with col_a:
        entry = st.number_input("Entry Price", value=1.3200, step=0.001, format="%.4f")
    with col_b:
        stop = st.number_input("Stop Price (defines 1R)", value=1.2500, step=0.001, format="%.4f")

    if entry > 0 and stop > 0 and entry != stop:
        levels = calculate_levels(entry, stop)
        r = levels["r_value"]

        st.subheader("Calculated Levels")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("1R (Stop)", f"${levels['stop']:.4f}")
        c2.metric("3R (TP1)", f"${levels['tp1']:.4f}")
        c3.metric("5R (TP2)", f"${levels['tp2']:.4f}")
        c4.metric("R Value", f"${r:.4f}")

        st.markdown(f"""
        **Unit Size:** ${UNIT_SIZE:,.0f}  
        **Risk per unit (approx):** ${levels['risk_usd']:.2f}
        """)

        # Simple visual
        prices = [stop, entry, levels["tp1"], levels["tp2"]]
        labels = ["1R Stop", "Entry", "3R", "5R"]
        chart_df = pd.DataFrame({"Level": labels, "Price": prices}).set_index("Level")
        st.bar_chart(chart_df)

    st.divider()
    st.subheader("Open Paper Trade (Demo)")
    st.write("No live open trades in this demo session. Connect the daily runner to populate real paper trades.")

# ------------------------------------------------------------
# PAGE: Backtesting
# ------------------------------------------------------------
elif page == "Backtesting":
    st.title("Backtesting Integration")
    st.caption("BASE formula • Fixed $2,000 units • 1R / 3R / 5R")

    df = get_sample_ohlcv(400)

    st.subheader("Run Parameters")
    c1, c2, c3 = st.columns(3)
    with c1:
        hold_days = st.slider("Hold Days", 5, 15, 10)
    with c2:
        pullback = st.slider("Min Pullback %", 5, 15, 10) / 100
    with c3:
        initial_equity = st.number_input("Initial Equity", value=10000, step=1000)

    if st.button("Run Backtest", type="primary"):
        with st.spinner("Running backtest..."):
            # Extremely simplified backtest for demo (not full engine)
            df = df.copy()
            df["sma200"] = df["close"].rolling(200, min_periods=50).mean()
            df["rsi"] = compute_rsi(df["close"])
            df["rise_10d"] = df["close"] / df["close"].shift(10) - 1

            trades = []
            in_trade = False
            entry_price = stop_price = entry_idx = None

            for i in range(50, len(df)):
                row = df.iloc[i]
                if not in_trade:
                    exhaustion = row["rise_10d"] >= 0.20 and row["rsi"] >= 75
                    local_high = df["high"].iloc[max(0, i-15):i+1].max()
                    pb = (local_high - row["close"]) / local_high if local_high > 0 else 0
                    holds = row["close"] >= row["sma200"] * 0.98 if pd.notna(row["sma200"]) else False

                    if exhaustion and pb >= pullback and holds:
                        entry_price = row["close"]
                        # Simple stop: 6% below entry for demo
                        stop_price = entry_price * 0.94
                        entry_idx = i
                        in_trade = True
                else:
                    hold = i - entry_idx
                    r = abs(entry_price - stop_price)
                    # Exit conditions
                    if row["close"] <= stop_price:
                        pnl_r = -1.0
                        reason = "stop_1R"
                        in_trade = False
                    elif row["close"] >= entry_price + 5 * r:
                        pnl_r = 5.0
                        reason = "tp2_5R"
                        in_trade = False
                    elif row["close"] >= entry_price + 3 * r:
                        pnl_r = 3.0
                        reason = "tp1_3R"
                        in_trade = False
                    elif hold >= hold_days:
                        pnl_r = (row["close"] - entry_price) / r
                        reason = "time_exit"
                        in_trade = False
                    else:
                        continue

                    trades.append({
                        "entry_date": df.index[entry_idx].date(),
                        "exit_date": df.index[i].date(),
                        "entry": round(entry_price, 4),
                        "exit": round(row["close"], 4),
                        "pnl_r": round(pnl_r, 2),
                        "reason": reason,
                        "hold_days": hold,
                    })

            trades_df = pd.DataFrame(trades)

            if trades_df.empty:
                st.warning("No trades generated with current parameters.")
            else:
                st.success(f"Generated {len(trades_df)} trades")

                # Summary metrics
                win_rate = (trades_df["pnl_r"] > 0).mean()
                avg_r = trades_df["pnl_r"].mean()
                total_r = trades_df["pnl_r"].sum()

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Trades", len(trades_df))
                m2.metric("Win Rate", f"{win_rate:.0%}")
                m3.metric("Avg R", f"{avg_r:+.2f}")
                m4.metric("Total R", f"{total_r:+.1f}")

                st.dataframe(trades_df, use_container_width=True)

                st.subheader("R-Multiple Distribution")
                st.bar_chart(trades_df["pnl_r"].value_counts().sort_index())

# ------------------------------------------------------------
# PAGE: SOL Day Scaffold
# ------------------------------------------------------------
elif page == "SOL Day (Scaffold)":
    st.title("SOL Day Trading")
    st.markdown("**Same unit model as XRP Swing**")

    st.info("Rules are not yet frozen. This section is a scaffold.")

    st.markdown(f"""
    ### Shared Unit Rules
    - Unit Size: **${UNIT_SIZE:,.0f}**
    - Max Loss: **1R**
    - Take Profit 1: **3R**
    - Take Profit 2: **5R**
    """)

    st.subheader("Next Steps to Freeze BASE Day Rules")
    st.markdown("""
    1. Choose primary timeframe (5m / 15m)
    2. Define trend filter + entry trigger
    3. Define how 1R stop is calculated
    4. Paper trade 20–30 times
    5. Run walk-forward validation
    6. Freeze the BASE day version
    """)

# ------------------------------------------------------------
# PAGE: About
# ------------------------------------------------------------
elif page == "About":
    st.title("About This Demo")
    st.markdown("""
    This demo showcases the core features of the **XRP Swing Formula** research system:

    - **BASE formula** signal with load-bar (all gates must be green)
    - **Standardized units**: $2,000 notional, 1R risk, 3R / 5R targets
    - **Paper trading** logic ready for daily automation
    - **Backtesting** integration (simplified for demo)
    - **SOL Day** scaffold using the same unit model

    The full research system lives in the repository:
    `projectfive01/xrp-swing-formula`

    > Not financial advice. Paper first. Small sample size warning still applies.
    """)
