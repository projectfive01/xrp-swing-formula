#!/usr/bin/env python3
"""
SOL Day v3 — Autonomous Runner (paper default, optional live)

Self-contained loop:
  1. Respect kill switch + daily loss limit (Chicago calendar)
  2. Fetch Binance 15m klines
  3. Detect Structure + ChoCh + first FVG ≥ configured ATR multiple
  4. Write local signal file
  5. Open paper trade when READY and entry guards pass (one at a time)
  6. If --live and BINANCE_LIVE=1: also place LIMIT + STOP on Binance
  7. Manage open trade on every loop (stop / 3R / 4R)
  8. Consume a setup fingerprint after open or an already-resolved skip
     so the same FVG cannot reprint after a close

Usage:
  python scripts/sol_day_autonomous_runner.py
  python scripts/sol_day_autonomous_runner.py --once
  python scripts/sol_day_autonomous_runner.py --poll 60
  BINANCE_LIVE=1 python scripts/sol_day_autonomous_runner.py --live

Kill switch:
  echo OFF > data/KILL_SWITCH.txt
  echo ON  > data/KILL_SWITCH.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
CFG_PATH = REPO / "backtest" / "config" / "sol_day_runtime.yaml"

LIVE_MODE = False
