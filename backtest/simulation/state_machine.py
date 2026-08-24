"""Trade state machine for backtests.

Mirrors the live SOL execution flow:
WAIT → READY → ENTERED → IN_TRADE → RISK_FREE → EXIT
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

from backtest.core.types import Setup, SimulatedTrade, TradeState, Direction


@dataclass
class StateMachine:
    risk_amount: float = 80.0
    state: TradeState = TradeState.WAIT
    current_setup: Optional[Setup] = None
    current_trade: Optional[SimulatedTrade] = None
    closed_trades: List[SimulatedTrade] = field(default_factory=list)

    def on_setup(self, setup: Setup):
        if self.state != TradeState.WAIT:
            return
        if setup.quality_score < 8:
            return
        self.current_setup = setup
        self.state = TradeState.READY

    def on_price(self, ts: datetime, price: float, opposite_choch: bool = False):
        if self.state == TradeState.READY:
            self._handle_ready(ts, price)
        elif self.state in (TradeState.ENTERED, TradeState.IN_TRADE):
            self._handle_in_trade(ts, price, opposite_choch)
        elif self.state == TradeState.RISK_FREE:
            self._handle_risk_free(ts, price, opposite_choch)
        elif self.state == TradeState.EXIT:
            self._finalize()

    def _handle_ready(self, ts: datetime, price: float):
        s = self.current_setup
        if s is None:
            self.state = TradeState.WAIT
            return

        # Invalidation
        if s.direction == Direction.LONG and price <= s.invalidation:
            self._cancel()
            return
        if s.direction == Direction.SHORT and price >= s.invalidation:
            self._cancel()
            return

        # Entry when price is inside FVG
        if s.fvg_low <= price <= s.fvg_high:
            one_r = abs(price - s.structural_stop)
            if one_r <= 0:
                self._cancel()
                return
            size = self.risk_amount / one_r
            self.current_trade = SimulatedTrade(
                setup=s,
                entry_price=price,
                stop_price=s.structural_stop,
                entry_ts=ts,
                size=size,
            )
            self.state = TradeState.IN_TRADE

    def _handle_in_trade(self, ts: datetime, price: float, opposite_choch: bool):
        t = self.current_trade
        s = self.current_setup
        if t is None or s is None:
            return

        # Stop hit
        if s.direction == Direction.LONG and price <= t.stop_price:
            self._exit(ts, price, "Structural Stop")
            return
        if s.direction == Direction.SHORT and price >= t.stop_price:
            self._exit(ts, price, "Structural Stop")
            return

        # Move to risk-free at +1R
        one_r = abs(t.entry_price - s.structural_stop)
        if s.direction == Direction.LONG and price >= t.entry_price + one_r:
            t.stop_price = t.entry_price
            self.state = TradeState.RISK_FREE
            return
        if s.direction == Direction.SHORT and price <= t.entry_price - one_r:
            t.stop_price = t.entry_price
            self.state = TradeState.RISK_FREE
            return

        if opposite_choch:
            self._exit(ts, price, "Opposite ChoCh")

    def _handle_risk_free(self, ts: datetime, price: float, opposite_choch: bool):
        t = self.current_trade
        s = self.current_setup
        if t is None or s is None:
            return

        if s.direction == Direction.LONG and price <= t.stop_price:
            self._exit(ts, price, "Break-even stop")
            return
        if s.direction == Direction.SHORT and price >= t.stop_price:
            self._exit(ts, price, "Break-even stop")
            return

        if opposite_choch:
            self._exit(ts, price, "Opposite ChoCh")

    def _exit(self, ts: datetime, price: float, reason: str):
        t = self.current_trade
        s = self.current_setup
        if t is None or s is None:
            return
        t.exit_price = price
        t.exit_ts = ts
        t.exit_reason = reason
        t.state_at_exit = self.state.value
        one_r = abs(t.entry_price - s.structural_stop)
        if one_r > 0:
            if s.direction == Direction.LONG:
                t.r_multiple = (price - t.entry_price) / one_r
            else:
                t.r_multiple = (t.entry_price - price) / one_r
        self.state = TradeState.EXIT

    def _finalize(self):
        if self.current_trade:
            self.closed_trades.append(self.current_trade)
        self.current_trade = None
        self.current_setup = None
        self.state = TradeState.WAIT

    def _cancel(self):
        self.current_setup = None
        self.current_trade = None
        self.state = TradeState.WAIT
