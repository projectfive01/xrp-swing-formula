"""Wilder ATR and volatility regime detection."""

from __future__ import annotations
import pandas as pd
import numpy as np


def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Vectorized Wilder ATR.
    Expects columns: high, low, close
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr


def volatility_ratio(atr: pd.Series, lookback_bars: int) -> float:
    """Current ATR / ATR from lookback_bars ago."""
    if len(atr) < lookback_bars + 1:
        return 1.0
    current = atr.iloc[-1]
    past = atr.iloc[-lookback_bars]
    if past == 0 or np.isnan(past) or np.isnan(current):
        return 1.0
    return float(current / past)


def get_regime(ratio: float) -> str:
    if ratio < 0.85:
        return "Low"
    if ratio > 1.20:
        return "High"
    return "Normal"
