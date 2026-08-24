"""CLI entry point for SOL Day backtests.

Usage:
    python -m backtest.runners.run_sol_day --days 90 --quality-min 8
    python -m backtest.runners.run_sol_day --days 30 --quality-min 8 --refresh
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from backtest.core.data_loader import load_candles
from backtest.core.types import Direction, Setup, TradeState
from backtest.detectors.sol_day import detect_setups
from backtest.simulation.state_machine import StateMachine
from backtest.analytics.metrics import compute_metrics

STORE_DIR = Path("backtest/store")


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def index_setups_by_bar(setups: List[Setup], df) -> Dict[int, List[Setup]]:
    """Map bar position -> setups whose ChoCh ts matches that bar."""
    ts_to_idx = {pd_ts_to_naive_key(ts): i for i, ts in enumerate(df["ts"])}
    by_bar: Dict[int, List[Setup]] = {}
    for s in setups:
        key = pd_ts_to_naive_key(s.ts)
        i = ts_to_idx.get(key)
        if i is None:
            # nearest match fallback
            continue
        by_bar.setdefault(i, []).append(s)
    return by_bar


def pd_ts_to_naive_key(ts) -> str:
    t = ts
    try:
        t = ts.to_pydatetime()
    except Exception:
        pass
    if getattr(t, "tzinfo", None) is not None:
        t = t.astimezone(timezone.utc).replace(tzinfo=None)
    return t.strftime("%Y-%m-%d %H:%M:%S")


def run_backtest(df, setups: List[Setup], risk_amount: float, quality_min: int) -> StateMachine:
    """
    Replay bars through the state machine.

    - On a bar where a qualifying setup appears, call on_setup
    - Each bar uses close as the decision price (conservative for backtest v1)
    - Opposite ChoCh approximated by a new setup in the opposite direction
    """
    engine = StateMachine(risk_amount=risk_amount)

    # Build quick lookup: bar index -> setups at that bar
    ts_keys = [pd_ts_to_naive_key(ts) for ts in df["ts"]]
    key_to_idx = {k: i for i, k in enumerate(ts_keys)}

    setups_at: Dict[int, List[Setup]] = {}
    for s in setups:
        if s.quality_score < quality_min:
            continue
        k = pd_ts_to_naive_key(s.ts)
        i = key_to_idx.get(k)
        if i is not None:
            setups_at.setdefault(i, []).append(s)

    for i in range(len(df)):
        ts = df["ts"].iloc[i]
        try:
            ts_py = ts.to_pydatetime()
        except Exception:
            ts_py = ts

        price = float(df["close"].iloc[i])
        bar_setups = setups_at.get(i, [])

        # Opposite ChoCh signal if in a trade and an opposite setup prints
        opposite = False
        if engine.current_setup is not None and bar_setups:
            for s in bar_setups:
                if s.direction != engine.current_setup.direction and s.quality_score >= quality_min:
                    opposite = True
                    break

        # Offer new setup only when idle
        if engine.state == TradeState.WAIT and bar_setups:
            # Take highest quality setup on this bar
            best = max(bar_setups, key=lambda x: x.quality_score)
            engine.on_setup(best)

        engine.on_price(ts_py, price, opposite_choch=opposite)

        # Ensure EXIT finalizes same bar
        if engine.state == TradeState.EXIT:
            engine.on_price(ts_py, price, opposite_choch=False)

    # If still in a trade at end of data, force flat at last close for reporting
    if engine.current_trade is not None and engine.state in (
        TradeState.IN_TRADE, TradeState.RISK_FREE, TradeState.ENTERED
    ):
        last_ts = df["ts"].iloc[-1]
        try:
            last_ts = last_ts.to_pydatetime()
        except Exception:
            pass
        last_price = float(df["close"].iloc[-1])
        engine._exit(last_ts, last_price, "End of data")
        engine._finalize()

    return engine


def print_report(metrics: dict, setups: List[Setup], trades, days: int, quality_min: int):
    print()
    print("=" * 60)
    print("SOL DAY BACKTEST REPORT")
    print("=" * 60)
    print(f"Days requested     : {days}")
    print(f"Quality minimum    : {quality_min}")
    print(f"Setups detected    : {len(setups)}")
    print(f"Trades closed      : {metrics.get('n', 0)}")
    print("-" * 60)
    print(f"Win rate           : {metrics.get('win_rate', 0):.1%}")
    print(f"Average R          : {metrics.get('avg_r', 0):.3f}")
    print(f"Avg win R          : {metrics.get('avg_win_r', 0):.3f}")
    print(f"Avg loss R         : {metrics.get('avg_loss_r', 0):.3f}")
    print(f"Expectancy         : {metrics.get('expectancy', 0):.3f} R")
    print(f"Total R            : {metrics.get('total_r', 0):.3f}")
    print(f"Max DD (R)         : {metrics.get('max_drawdown_r', 0):.3f}")
    print("-" * 60)

    if setups:
        from collections import Counter
        q_counts = Counter(int(s.quality_score) for s in setups)
        print("Setups by Quality Score:")
        for q in sorted(q_counts):
            print(f"  Q{q}: {q_counts[q]}")

    if trades:
        print()
        print("Recent trades:")
        for t in trades[-8:]:
            d = t.setup.direction.value if t.setup else "?"
            r = f"{t.r_multiple:.2f}R" if t.r_multiple is not None else "n/a"
            print(
                f"  {t.entry_ts} {d:5s} entry={t.entry_price:.4f} "
                f"exit={t.exit_price:.4f} {r:>8s}  {t.exit_reason}"
            )
    print("=" * 60)


def persist_run(run_id: str, metrics: dict, params: dict, trades):
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    runs_path = STORE_DIR / "backtest_runs.jsonl"
    trades_path = STORE_DIR / "backtest_trades.jsonl"

    run_row = {
        "run_id": run_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "front": "sol_day",
        "metrics": metrics,
        "params": params,
    }
    with open(runs_path, "a") as f:
        f.write(json.dumps(run_row, default=str) + "\n")

    with open(trades_path, "a") as f:
        for t in trades:
            row = {
                "run_id": run_id,
                "direction": t.setup.direction.value if t.setup else None,
                "quality_score": t.setup.quality_score if t.setup else None,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "r_multiple": t.r_multiple,
                "exit_reason": t.exit_reason,
                "entry_ts": str(t.entry_ts),
                "exit_ts": str(t.exit_ts),
                "regime": t.setup.volatility_regime if t.setup else None,
            }
            f.write(json.dumps(row, default=str) + "\n")


def main():
    parser = argparse.ArgumentParser(description="SOL Day backtest runner")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--quality-min", type=int, default=8)
    parser.add_argument("--config", type=str, default="backtest/config/sol_day.yaml")
    parser.add_argument("--refresh", action="store_true", help="Force re-download candles")
    parser.add_argument("--return-all-setups", action="store_true",
                        help="Score all setups then filter (for analysis)")
    parser.add_argument("--no-store", action="store_true", help="Skip JSONL persistence")
    args = parser.parse_args()

    config = load_config(args.config)
    symbol = config.get("symbol", "SOLUSDT")
    timeframe = config.get("timeframe", "5m")
    risk_amount = float(config.get("risk", {}).get("base_risk_usd", 80))

    print("SOL Day backtest")
    print(f"  symbol      : {symbol}")
    print(f"  timeframe   : {timeframe}")
    print(f"  days        : {args.days}")
    print(f"  quality_min : {args.quality_min}")
    print(f"  risk_amount : ${risk_amount}")
    print()

    print("Loading candles...")
    df = load_candles(
        symbol=symbol,
        interval=timeframe,
        days=args.days,
        refresh=args.refresh,
    )
    if df.empty:
        print("ERROR: no candle data returned")
        return
    print(f"  bars: {len(df)}  range: {df['ts'].iloc[0]} → {df['ts'].iloc[-1]}")

    print("Detecting setups...")
    setups = detect_setups(
        df,
        config,
        quality_min=args.quality_min if not args.return_all_setups else 0,
        return_all=args.return_all_setups,
    )
    # If return_all, still simulate only quality_min+
    sim_setups = [s for s in setups if s.quality_score >= args.quality_min]
    print(f"  setups scored: {len(setups)}  eligible (>= {args.quality_min}): {len(sim_setups)}")

    print("Simulating trades...")
    engine = run_backtest(df, sim_setups, risk_amount=risk_amount, quality_min=args.quality_min)
    trades = engine.closed_trades
    metrics = compute_metrics(trades)

    print_report(metrics, setups if args.return_all_setups else sim_setups, trades, args.days, args.quality_min)

    if not args.no_store:
        run_id = f"sol-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "days": args.days,
            "quality_min": args.quality_min,
            "risk_amount": risk_amount,
            "bars": len(df),
        }
        persist_run(run_id, metrics, params, trades)
        print(f"Stored run_id={run_id} → backtest/store/")


if __name__ == "__main__":
    main()
