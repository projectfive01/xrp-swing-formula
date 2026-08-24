"""Performance metrics for backtest runs."""

from __future__ import annotations
from typing import List
import numpy as np

from backtest.core.types import SimulatedTrade, BacktestResult


def compute_metrics(trades: List[SimulatedTrade]) -> dict:
    if not trades:
        return {
            "n": 0,
            "win_rate": 0.0,
            "avg_r": 0.0,
            "avg_win_r": 0.0,
            "avg_loss_r": 0.0,
            "expectancy": 0.0,
            "total_r": 0.0,
            "max_drawdown_r": 0.0,
        }

    rs = [t.r_multiple for t in trades if t.r_multiple is not None]
    if not rs:
        return {"n": len(trades), "error": "no r_multiples"}

    wins = [r for r in rs if r > 0.05]
    losses = [r for r in rs if r < -0.05]

    n = len(rs)
    win_rate = len(wins) / n if n else 0.0
    avg_r = float(np.mean(rs))
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
    total_r = float(np.sum(rs))

    # Simple R drawdown
    equity = np.cumsum(rs)
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = float(dd.min()) if len(dd) else 0.0

    return {
        "n": n,
        "win_rate": round(win_rate, 4),
        "avg_r": round(avg_r, 4),
        "avg_win_r": round(avg_win, 4),
        "avg_loss_r": round(avg_loss, 4),
        "expectancy": round(expectancy, 4),
        "total_r": round(total_r, 4),
        "max_drawdown_r": round(max_dd, 4),
    }
