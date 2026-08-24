"""SOL Day setup detector (ChoCh + FVG + Quality Score).

Enhanced path aligned with RESEARCH_ENHANCEMENTS.md and ATR regime thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from backtest.core.types import Setup, Direction
from backtest.core.atr import wilder_atr, get_regime


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _regime_thresholds(config: dict, regime: str) -> dict:
    regimes = config.get("regimes", {})
    defaults = {
        "Low": {"fvg_strong": 0.85, "fvg_accept": 0.50, "stop_min": 0.50, "stop_max": 1.80},
        "Normal": {"fvg_strong": 1.00, "fvg_accept": 0.60, "stop_min": 0.60, "stop_max": 2.00},
        "High": {"fvg_strong": 1.20, "fvg_accept": 0.75, "stop_min": 0.75, "stop_max": 2.30},
    }
    base = defaults.get(regime, defaults["Normal"]).copy()
    # Overlay from config if present
    key = regime.lower()
    if key in regimes:
        for k, v in regimes[key].items():
            if k.startswith("fvg_") or k.startswith("stop_"):
                base[k] = v
    return base


def score_setup(structure: int, choch: int, fvg: int, location: int, context: int) -> int:
    """Each component is 0–2. Total 0–10."""
    return int(max(0, min(2, structure)) +
               max(0, min(2, choch)) +
               max(0, min(2, fvg)) +
               max(0, min(2, location)) +
               max(0, min(2, context)))


# ---------------------------------------------------------------------------
# Swing detection
# ---------------------------------------------------------------------------

@dataclass
class Swing:
    index: int
    ts: datetime
    price: float
    kind: str  # "high" or "low"


def find_swings(df: pd.DataFrame, left: int = 3, right: int = 3) -> List[Swing]:
    """
    Pivot swings: a high is a swing high if it is the max of left+right+1 bars.
    Same for lows.
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)
    swings: List[Swing] = []

    for i in range(left, n - right):
        window_h = highs[i - left: i + right + 1]
        window_l = lows[i - left: i + right + 1]
        if highs[i] == np.max(window_h) and np.sum(window_h == highs[i]) == 1:
            swings.append(Swing(i, df["ts"].iloc[i], float(highs[i]), "high"))
        if lows[i] == np.min(window_l) and np.sum(window_l == lows[i]) == 1:
            swings.append(Swing(i, df["ts"].iloc[i], float(lows[i]), "low"))

    swings.sort(key=lambda s: s.index)
    return swings


def recent_structure_bias(swings: List[Swing], up_to_index: int) -> Tuple[str, int]:
    """
    Returns (bias, clarity_score 0-2).
    bias: 'bullish', 'bearish', or 'neutral'
    clarity based on last 2-3 comparable swings.
    """
    prior = [s for s in swings if s.index < up_to_index]
    if len(prior) < 4:
        return "neutral", 0

    highs = [s for s in prior if s.kind == "high"][-3:]
    lows = [s for s in prior if s.kind == "low"][-3:]

    hh = len(highs) >= 2 and highs[-1].price > highs[-2].price
    hl = len(lows) >= 2 and lows[-1].price > lows[-2].price
    lh = len(highs) >= 2 and highs[-1].price < highs[-2].price
    ll = len(lows) >= 2 and lows[-1].price < lows[-2].price

    if hh and hl:
        clarity = 2 if len(highs) >= 3 and len(lows) >= 3 else 1
        return "bullish", clarity
    if lh and ll:
        clarity = 2 if len(highs) >= 3 and len(lows) >= 3 else 1
        return "bearish", clarity
    return "neutral", 0


# ---------------------------------------------------------------------------
# ChoCh detection
# ---------------------------------------------------------------------------

@dataclass
class ChoChEvent:
    index: int
    ts: datetime
    direction: Direction  # direction of the NEW trade bias after ChoCh
    level: float          # broken swing level
    swing_index: int
    close: float
    body_ratio: float     # body / range of the breaking candle


def detect_choch_events(df: pd.DataFrame, swings: List[Swing]) -> List[ChoChEvent]:
    """
    Change of Character:
    - Bullish ChoCh: close breaks above a prior swing high after bearish/neutral structure
    - Bearish ChoCh: close breaks below a prior swing low after bullish/neutral structure
    """
    events: List[ChoChEvent] = []
    closes = df["close"].values
    opens = df["open"].values
    highs = df["high"].values
    lows = df["low"].values

    for i in range(1, len(df)):
        bias, _ = recent_structure_bias(swings, i)
        prior_swings = [s for s in swings if s.index < i]
        if not prior_swings:
            continue

        # Most recent opposite swing to break
        last_high = next((s for s in reversed(prior_swings) if s.kind == "high"), None)
        last_low = next((s for s in reversed(prior_swings) if s.kind == "low"), None)

        range_ = max(highs[i] - lows[i], 1e-12)
        body = abs(closes[i] - opens[i])
        body_ratio = body / range_

        # Bullish ChoCh: close above last swing high (shift from down/neutral to up)
        if last_high and closes[i] > last_high.price and closes[i - 1] <= last_high.price:
            if bias in ("bearish", "neutral"):
                events.append(ChoChEvent(
                    index=i,
                    ts=df["ts"].iloc[i],
                    direction=Direction.LONG,
                    level=last_high.price,
                    swing_index=last_high.index,
                    close=float(closes[i]),
                    body_ratio=float(body_ratio),
                ))

        # Bearish ChoCh: close below last swing low
        if last_low and closes[i] < last_low.price and closes[i - 1] >= last_low.price:
            if bias in ("bullish", "neutral"):
                events.append(ChoChEvent(
                    index=i,
                    ts=df["ts"].iloc[i],
                    direction=Direction.SHORT,
                    level=last_low.price,
                    swing_index=last_low.index,
                    close=float(closes[i]),
                    body_ratio=float(body_ratio),
                ))

    return events


# ---------------------------------------------------------------------------
# FVG detection
# ---------------------------------------------------------------------------

@dataclass
class FVG:
    index: int          # index of the 3rd candle in the pattern
    ts: datetime
    direction: Direction
    high: float         # top of gap
    low: float          # bottom of gap
    size: float


def detect_fvg_at(df: pd.DataFrame, i: int, direction: Direction) -> Optional[FVG]:
    """
    Classic 3-candle FVG ending at index i.
    Bullish: candle[i-2].high < candle[i].low
    Bearish: candle[i-2].low > candle[i].high
    """
    if i < 2:
        return None

    c0_high = float(df["high"].iloc[i - 2])
    c0_low = float(df["low"].iloc[i - 2])
    c2_high = float(df["high"].iloc[i])
    c2_low = float(df["low"].iloc[i])

    if direction == Direction.LONG:
        if c0_high < c2_low:
            gap_low = c0_high
            gap_high = c2_low
            return FVG(i, df["ts"].iloc[i], Direction.LONG, gap_high, gap_low, gap_high - gap_low)
    else:
        if c0_low > c2_high:
            gap_high = c0_low
            gap_low = c2_high
            return FVG(i, df["ts"].iloc[i], Direction.SHORT, gap_high, gap_low, gap_high - gap_low)

    return None


def first_fvg_after_choch(
    df: pd.DataFrame,
    choch: ChoChEvent,
    max_bars: int = 5,
) -> Optional[FVG]:
    """Prefer the first clean FVG within a few bars after ChoCh."""
    start = choch.index
    end = min(len(df) - 1, start + max_bars)
    for i in range(start, end + 1):
        fvg = detect_fvg_at(df, i, choch.direction)
        if fvg is not None and fvg.size > 0:
            return fvg
    return None


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_choch_quality(choch: ChoChEvent) -> int:
    # Decisive body close beyond swing
    if choch.body_ratio >= 0.55:
        return 2
    if choch.body_ratio >= 0.30:
        return 1
    return 0


def score_fvg_quality(fvg: FVG, atr_value: float, thresholds: dict) -> int:
    if atr_value <= 0:
        return 0
    ratio = fvg.size / atr_value
    if ratio >= thresholds["fvg_strong"]:
        return 2
    if ratio >= thresholds["fvg_accept"]:
        return 1
    return 0


def score_location(df: pd.DataFrame, choch: ChoChEvent, fvg: FVG, lookback: int = 30) -> int:
    """
    Rough premium/discount scoring vs recent range.
    Long wants FVG in lower half (discount); short in upper half (premium).
    """
    start = max(0, choch.index - lookback)
    window = df.iloc[start: choch.index + 1]
    if window.empty:
        return 0

    hi = float(window["high"].max())
    lo = float(window["low"].min())
    if hi <= lo:
        return 0

    mid = (hi + lo) / 2.0
    fvg_mid = (fvg.high + fvg.low) / 2.0

    if choch.direction == Direction.LONG:
        if fvg_mid <= mid:
            return 2 if fvg_mid <= lo + 0.35 * (hi - lo) else 1
        return 0
    else:
        if fvg_mid >= mid:
            return 2 if fvg_mid >= lo + 0.65 * (hi - lo) else 1
        return 0


def score_context(ts: datetime, config: dict, extra_confluence: bool = False) -> int:
    """
    Session preference + optional confluence flag.
    Config session times are America/Chicago wall times as strings HH:MM.
    """
    session = config.get("session", {})
    # Without full timezone conversion of every bar, use UTC hour heuristic
    # NY cash open region roughly 13:30–20:00 UTC
    hour = ts.hour if hasattr(ts, "hour") else pd.Timestamp(ts).hour
    in_ny = 13 <= hour <= 20

    if in_ny and extra_confluence:
        return 2
    if in_ny or extra_confluence:
        return 1
    return 0


def structural_stop_and_invalidation(
    df: pd.DataFrame,
    choch: ChoChEvent,
    fvg: FVG,
    atr_value: float,
    thresholds: dict,
) -> Optional[Tuple[float, float]]:
    """
    Stop beyond the swing that defined the ChoCh, with ATR guardrails.
    Invalidation slightly beyond that stop.
    """
    if choch.direction == Direction.LONG:
        stop = float(df["low"].iloc[choch.swing_index: choch.index + 1].min())
        # Prefer stop below FVG low if tighter but still valid
        stop = min(stop, fvg.low)
        dist = abs(fvg.high - stop)  # conservative distance proxy from entry zone
    else:
        stop = float(df["high"].iloc[choch.swing_index: choch.index + 1].max())
        stop = max(stop, fvg.high)
        dist = abs(stop - fvg.low)

    if atr_value > 0:
        if dist < thresholds["stop_min"] * atr_value:
            return None  # too tight
        if dist > thresholds["stop_max"] * atr_value:
            return None  # too wide for this regime

    if choch.direction == Direction.LONG:
        invalidation = stop - 0.1 * atr_value if atr_value > 0 else stop
    else:
        invalidation = stop + 0.1 * atr_value if atr_value > 0 else stop

    return stop, invalidation


# ---------------------------------------------------------------------------
# Main detector
# ---------------------------------------------------------------------------

def detect_setups(
    df: pd.DataFrame,
    config: dict,
    quality_min: Optional[int] = None,
    return_all: bool = False,
) -> List[Setup]:
    """
    Scan candles and return SOL Day setups.

    Parameters
    ----------
    df : DataFrame with columns ts, open, high, low, close
    config : loaded sol_day.yaml (dict)
    quality_min : override config quality_min
    return_all : if True, return all scored setups; else only >= quality_min
    """
    if df is None or df.empty or len(df) < 30:
        return []

    required = {"ts", "open", "high", "low", "close"}
    if not required.issubset(df.columns):
        raise ValueError(f"DataFrame missing columns: {required - set(df.columns)}")

    qmin = quality_min if quality_min is not None else int(config.get("quality_min", 8))
    atr_period = int(config.get("atr", {}).get("period", 14))
    lookback_days = float(config.get("atr", {}).get("lookback_days_for_regime", 3))
    bars_per_day = 288  # 5m
    lookback_bars = int(lookback_days * bars_per_day)

    work = df.reset_index(drop=True).copy()
    atr_series = wilder_atr(work, period=atr_period)
    swings = find_swings(work, left=3, right=3)
    choch_events = detect_choch_events(work, swings)

    setups: List[Setup] = []

    for choch in choch_events:
        atr_value = float(atr_series.iloc[choch.index]) if not np.isnan(atr_series.iloc[choch.index]) else 0.0
        if atr_value <= 0:
            continue

        # Regime from ATR ratio
        if choch.index >= lookback_bars:
            past_atr = float(atr_series.iloc[choch.index - lookback_bars])
            ratio = (atr_value / past_atr) if past_atr > 0 else 1.0
        else:
            ratio = 1.0
        regime = get_regime(ratio)
        thresholds = _regime_thresholds(config, regime)

        fvg = first_fvg_after_choch(work, choch, max_bars=5)
        if fvg is None:
            continue

        stop_inv = structural_stop_and_invalidation(work, choch, fvg, atr_value, thresholds)
        if stop_inv is None:
            continue
        structural_stop, invalidation = stop_inv

        # --- Quality components ---
        _, structure_pts = recent_structure_bias(swings, choch.index)
        # If bias matched the break context, boost structure slightly when neutral	o directional
        if structure_pts == 0:
            structure_pts = 1  # ChoCh itself implies some structure shift

        choch_pts = score_choch_quality(choch)
        fvg_pts = score_fvg_quality(fvg, atr_value, thresholds)
        location_pts = score_location(work, choch, fvg)
        context_pts = score_context(choch.ts, config, extra_confluence=False)

        q = score_setup(structure_pts, choch_pts, fvg_pts, location_pts, context_pts)

        if (not return_all) and q < qmin:
            continue

        setups.append(Setup(
            ts=choch.ts if hasattr(choch.ts, "to_pydatetime") else pd.Timestamp(choch.ts).to_pydatetime(),
            direction=choch.direction,
            quality_score=float(q),
            choch_level=float(choch.level),
            fvg_high=float(fvg.high),
            fvg_low=float(fvg.low),
            structural_stop=float(structural_stop),
            invalidation=float(invalidation),
            atr=float(atr_value),
            volatility_regime=regime,
            metadata={
                "structure_pts": structure_pts,
                "choch_pts": choch_pts,
                "fvg_pts": fvg_pts,
                "location_pts": location_pts,
                "context_pts": context_pts,
                "fvg_size": fvg.size,
                "choch_index": choch.index,
                "fvg_index": fvg.index,
                "body_ratio": choch.body_ratio,
                "atr_ratio": ratio,
            },
        ))

    return setups
