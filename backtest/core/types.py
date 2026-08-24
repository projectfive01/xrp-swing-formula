"""Shared dataclasses for the backtest pipeline."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeState(str, Enum):
    WAIT = "WAIT"
    READY = "READY"
    ENTERED = "ENTERED"
    IN_TRADE = "IN_TRADE"
    RISK_FREE = "RISK_FREE"
    EXIT = "EXIT"


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Setup:
    ts: datetime
    direction: Direction
    quality_score: float
    choch_level: float
    fvg_high: float
    fvg_low: float
    structural_stop: float
    invalidation: float
    atr: float
    volatility_regime: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SimulatedTrade:
    setup: Setup
    entry_price: float
    stop_price: float
    exit_price: Optional[float] = None
    entry_ts: Optional[datetime] = None
    exit_ts: Optional[datetime] = None
    exit_reason: Optional[str] = None
    r_multiple: Optional[float] = None
    size: float = 0.0
    state_at_exit: Optional[str] = None


@dataclass
class BacktestResult:
    run_id: str
    symbol: str
    start: datetime
    end: datetime
    trades: List[SimulatedTrade]
    win_rate: float = 0.0
    avg_r: float = 0.0
    expectancy: float = 0.0
    total_r: float = 0.0
    max_drawdown_r: float = 0.0
    params: dict = field(default_factory=dict)
