"""
Paper Trader — Fixed $2,000 Units | 1R Risk | 3R / 5R Targets
Works for both XRP Swing (BASE) and future SOL Day trades.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import pandas as pd


class PaperTrader:
    """
    Paper trading engine using standardized units.

    Unit Rules (frozen):
    - Unit size      = $2,000 notional
    - Max loss       = 1R
    - Take Profit 1  = 3R (scale out)
    - Take Profit 2  = 5R
    """

    UNIT_SIZE_USD = 2000.0

    def __init__(
        self,
        data_dir: str | Path = "data",
        trades_file: str = "trades.jsonl",
        open_trades_file: str = "open_trades.json",
    ):
        self.data_dir = Path(data_dir)
        self.trades_file = self.data_dir / trades_file
        self.open_trades_file = self.data_dir / open_trades_file
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load_open_trades(self) -> List[Dict]:
        if not self.open_trades_file.exists():
            return []
        with open(self.open_trades_file) as f:
            return json.load(f)

    def _save_open_trades(self, trades: List[Dict]):
        with open(self.open_trades_file, "w") as f:
            json.dump(trades, f, indent=2, default=str)

    def _append_closed_trade(self, trade: Dict):
        with open(self.trades_file, "a") as f:
            f.write(json.dumps(trade, default=str) + "\n")

    # ------------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_levels(entry_price: float, stop_price: float) -> Dict[str, float]:
        """
        Given entry and stop, return R value and target prices.
        Assumes long trades (stop < entry).
        """
        r_value = abs(entry_price - stop_price)
        if r_value == 0:
            raise ValueError("Stop price cannot equal entry price")

        return {
            "r_value": r_value,
            "stop_price": stop_price,
            "tp1_price": entry_price + 3 * r_value,   # 3R
            "tp2_price": entry_price + 5 * r_value,   # 5R
        }

    # ------------------------------------------------------------------
    # Main daily update
    # ------------------------------------------------------------------
    def update(
        self,
        current_price: float,
        signal_action: str,
        entry_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        bar_timestamp: Optional[str] = None,
        variant: str = "BASE",
        extra_meta: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Call this once per day (or per bar for day trading).

        Parameters
        ----------
        current_price : float
            Latest close / mark price
        signal_action : str
            "BUY" or "HOLD"
        entry_price, stop_price : float, optional
            Required when opening a new trade (signal_action == "BUY")
        """
        ts = bar_timestamp or datetime.now(timezone.utc).isoformat()
        open_trades = self._load_open_trades()
        still_open = []
        closed_today = []
        new_trade = None

        # ----- Manage existing open trades -----
        for trade in open_trades:
            entry = trade["entry_price"]
            r_value = trade["r_value"]
            unrealized_r = (current_price - entry) / r_value

            # Update MAE / MFE in R terms
            trade["mae_r"] = min(trade.get("mae_r", 0.0), unrealized_r)
            trade["mfe_r"] = max(trade.get("mfe_r", 0.0), unrealized_r)
            trade["last_price"] = current_price
            trade["unrealized_r"] = unrealized_r

            should_exit = False
            exit_reason = ""
            exit_r = unrealized_r

            # 1R stop
            if current_price <= trade["stop_price"]:
                should_exit = True
                exit_reason = "stop_1R"
                exit_r = -1.0

            # 5R final target
            elif current_price >= trade["tp2_price"]:
                should_exit = True
                exit_reason = "tp2_5R"
                exit_r = 5.0

            # 3R scale-out (simple version: close full size at 3R for now)
            # Later we can implement partial scaling
            elif current_price >= trade["tp1_price"] and not trade.get("tp1_hit"):
                should_exit = True
                exit_reason = "tp1_3R"
                exit_r = 3.0
                trade["tp1_hit"] = True

            if should_exit:
                closed = {
                    **trade,
                    "exit_time": ts,
                    "exit_price": current_price,
                    "exit_reason": exit_reason,
                    "pnl_r": exit_r,
                    "pnl_usd": exit_r * (trade["unit_size_usd"] * (r_value / entry)),  # approx
                    "status": "CLOSED",
                }
                self._append_closed_trade(closed)
                closed_today.append(closed)
            else:
                still_open.append(trade)

        # ----- Open new trade if BUY and flat -----
        if signal_action == "BUY" and len(still_open) == 0 and entry_price and stop_price:
            levels = self.calculate_levels(entry_price, stop_price)

            new_trade = {
                "entry_time": ts,
                "entry_price": entry_price,
                "unit_size_usd": self.UNIT_SIZE_USD,
                "r_value": levels["r_value"],
                "stop_price": levels["stop_price"],
                "tp1_price": levels["tp1_price"],
                "tp2_price": levels["tp2_price"],
                "mae_r": 0.0,
                "mfe_r": 0.0,
                "last_price": entry_price,
                "unrealized_r": 0.0,
                "status": "OPEN",
                "variant": variant,
                "notes": "PAPER",
                **(extra_meta or {}),
            }
            still_open.append(new_trade)

        self._save_open_trades(still_open)

        return {
            "timestamp": ts,
            "action": signal_action,
            "open_trades": still_open,
            "closed_today": closed_today,
            "new_trade": new_trade,
        }


# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------
if __name__ == "__main__":
    pt = PaperTrader(data_dir="data")

    # Example: new BUY signal
    result = pt.update(
        current_price=1.32,
        signal_action="BUY",
        entry_price=1.32,
        stop_price=1.25,          # this defines 1R
        variant="BASE",
    )
    print(json.dumps(result, indent=2, default=str))
