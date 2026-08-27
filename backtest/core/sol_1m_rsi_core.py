"""SOL 1m RSI-S CORE — locked formula helpers.

Formula (DO NOT CHANGE):
  timeframe      1m
  RSI            Wilder period 14 on CLOSED 1m closes only
  long           closed RSI <= 20
  short          closed RSI >= 80
  stop           1 * ATR(14) beyond entry  (= 1R)
  target         2R
  session hours  UTC {7, 10, 11, 20}
  paper risk     1.0% of equity
  daily cap      3.0R
  one trade      at a time

This module is the formula. Runners may change data plumbing,
logging, and retries — not these thresholds.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

RSI_PERIOD = 14
ATR_PERIOD = 14
RSI_LONG = 20.0
RSI_SHORT = 80.0
STOP_ATR_MULT = 1.0
TARGET_R = 2.0
SESSION_HOURS_UTC = (7, 10, 11, 20)
RISK_PCT = 0.01
DAILY_CAP_R = 3.0
PAPER_EQUITY_START = 2000.0


def wilder_rsi(closes: np.ndarray, period: int = RSI_PERIOD) -> np.ndarray:
    """Wilder RSI. Returns array same length as closes; early bars are nan."""
    n = len(closes)
    out = np.full(n, np.nan, dtype=float)
    if n < period + 1:
        return out
    delta = np.diff(closes)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    if avg_loss == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    for i in range(period, n - 1):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return out


def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = ATR_PERIOD) -> np.ndarray:
    n = len(close)
    atr = np.full(n, np.nan, dtype=float)
    if n < period + 1:
        return atr
    prev = close[:-1]
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - prev), np.abs(low[1:] - prev)))
    atr[period] = float(np.mean(tr[:period]))
    for i in range(period, len(tr)):
        atr[i + 1] = (atr[i] * (period - 1) + tr[i]) / period
    return atr


def in_session(hour_utc: int) -> bool:
    return int(hour_utc) in SESSION_HOURS_UTC


def signal_from_closed_rsi(rsi_closed: float) -> str:
    if rsi_closed <= RSI_LONG:
        return "LONG"
    if rsi_closed >= RSI_SHORT:
        return "SHORT"
    return "WAIT"


def levels(direction: str, entry: float, atr: float) -> Optional[dict]:
    if atr <= 0 or not np.isfinite(atr):
        return None
    risk = STOP_ATR_MULT * float(atr)
    if direction == "LONG":
        stop = entry - risk
        tgt = entry + TARGET_R * risk
    elif direction == "SHORT":
        stop = entry + risk
        tgt = entry - TARGET_R * risk
    else:
        return None
    return {"stop": stop, "tgt": tgt, "r_value": risk}
