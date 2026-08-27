"""Config, IO, market data helpers for the SOL Day autonomous runner."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
CFG_PATH = REPO / "backtest" / "config" / "sol_day_runtime.yaml"


def load_dotenv() -> None:
    env_path = REPO / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_cfg() -> dict:
    defaults = {
        "symbol": "SOLUSDT",
        "timeframe": "15m",
        "poll_seconds": 120,
        "equity_unit_usd": 1000.0,
        "kelly_fraction": 0.045,
        "max_risk_pct": 0.05,
        "daily_loss_limit_pct": 0.08,
        "fvg_min_atr_multiple": 0.60,
        "signal_fresh_minutes": 90,
        "max_entry_distance_r": 1.25,
        "one_trade_at_a_time": True,
        "session": {"timezone": "America/Chicago"},
        "paths": {
            "kill_switch": "data/KILL_SWITCH.txt",
            "open_trades": "data/sol_day_open_trades.json",
            "closed_trades": "data/sol_day_paper_trades.jsonl",
            "latest_signal": "data/sol_day_latest_signal.json",
            "daily_state": "data/sol_day_daily_state.json",
        },
    }
    if not CFG_PATH.exists():
        return defaults
    text = CFG_PATH.read_text()
    cfg = dict(defaults)
    section = None
    for raw in text.splitlines():
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            key = line[:-1].strip()
            if key == "paths":
                section = "paths"
                cfg.setdefault("paths", {})
            elif key == "session":
                section = "session"
                cfg.setdefault("session", {})
            else:
                section = None
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if section == "paths":
            cfg["paths"][k] = v
        elif section == "session":
            if v.lower() in ("true", "false"):
                cfg.setdefault("session", {})[k] = v.lower() == "true"
            else:
                cfg.setdefault("session", {})[k] = v
        else:
            if v.lower() in ("true", "false"):
                cfg[k] = v.lower() == "true"
            else:
                try:
                    cfg[k] = float(v) if "." in v else int(v)
                except ValueError:
                    cfg[k] = v
    return cfg


def p(path_key: str, cfg: dict) -> Path:
    return REPO / cfg["paths"][path_key]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def session_tz(cfg: dict) -> ZoneInfo:
    name = "America/Chicago"
    sess = cfg.get("session") or {}
    if isinstance(sess, dict) and sess.get("timezone"):
        name = str(sess["timezone"])
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("America/Chicago")


def trading_date(cfg: dict) -> str:
    return datetime.now(session_tz(cfg)).strftime("%Y-%m-%d")


def kline_iso(klines, idx: int) -> str:
    return datetime.fromtimestamp(int(klines[idx][0]) / 1000, tz=timezone.utc).isoformat()


def kill_on(cfg: dict) -> bool:
    f = p("kill_switch", cfg)
    if not f.exists():
        return False
    return f.read_text().strip().upper().startswith("ON")


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text() or json.dumps(default))
    except Exception:
        return default


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str) + "\n")


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, default=str) + "\n")


def fetch_klines(symbol: str, interval: str, limit: int = 300) -> list:
    url = (
        f"https://data-api.binance.vision/api/v3/klines"
        f"?symbol={symbol}&interval={interval}&limit={limit}"
    )
    req = Request(url, headers={"User-Agent": "sol-day-runner/1.0"})
    with urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fetch_price(symbol: str) -> float:
    url = f"https://data-api.binance.vision/api/v3/ticker/price?symbol={symbol}"
    req = Request(url, headers={"User-Agent": "sol-day-runner/1.0"})
    with urlopen(req, timeout=15) as r:
        return float(json.loads(r.read().decode())["price"])
