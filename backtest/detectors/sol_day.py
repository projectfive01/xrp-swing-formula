"""SOL Day setup detector (ChoCh + FVG + Quality Score).

This is the enhanced path. Implementation will fill in structure detection.
"""

from __future__ import annotations
from typing import List
import pandas as pd

from backtest.core.types import Setup, Direction
from backtest.core.atr import wilder_atr, volatility_ratio, get_regime


def score_setup(
    structure: int,
    choch: int,
    fvg: int,
    location: int,
    context: int,
) -> int:
    """Each component is 0–2. Total 0–10."""
    return int(structure + choch + fvg + location + context)


def detect_setups(df: pd.DataFrame, config: dict) -> List[Setup]:
    """
    Scan candles and return candidate setups.

    TODO:
    - Implement swing / ChoCh detection
    - Implement FVG detection after ChoCh
    - Apply ATR regime thresholds for FVG size
    - Apply session filter
    - Return only setups with quality_score >= config['quality_min']
      (or return all and filter upstream for analysis)
    """
    if df.empty:
        return []

    # Placeholder: real detection logic goes here
    atr = wilder_atr(df, period=config.get("atr", {}).get("period", 14))
    # ratio / regime will be used when scoring FVGs and stops

    setups: List[Setup] = []
    return setups
