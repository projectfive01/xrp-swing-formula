"""CLI entry point for SOL Day backtests.

Usage (target):
    python -m backtest.runners.run_sol_day --days 90 --quality-min 8
"""

from __future__ import annotations
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import json

# from backtest.core.data_loader import load_candles
# from backtest.detectors.sol_day import detect_setups
# from backtest.simulation.state_machine import StateMachine
# from backtest.analytics.metrics import compute_metrics


def main():
    parser = argparse.ArgumentParser(description="SOL Day backtest runner")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--quality-min", type=int, default=8)
    parser.add_argument("--config", type=str, default="backtest/config/sol_day.yaml")
    args = parser.parse_args()

    print("SOL Day backtest runner (stub)")
    print(f"  days         : {args.days}")
    print(f"  quality_min  : {args.quality_min}")
    print(f"  config       : {args.config}")
    print()
    print("Next implementation steps:")
    print("  1. Load candles via core.data_loader")
    print("  2. detect_setups() with Quality Score")
    print("  3. Replay through StateMachine")
    print("  4. compute_metrics() and write to store/")
    print()
    print("This stub exists so the 30-day build path has a clear entry point.")


if __name__ == "__main__":
    main()
