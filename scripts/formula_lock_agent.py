#!/usr/bin/env python3
"""Formula lock + desk heartbeat agent.

Does not trade. Compares frozen specs to running code and writes
data/formula_lock_status.json for the command board.

  python scripts/formula_lock_agent.py --once
  python scripts/formula_lock_agent.py --poll 30
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

LOCK_PATH = REPO / "backtest" / "config" / "formula_locks.json"
STATUS_PATH = REPO / "data" / "formula_lock_status.json"
CORE = REPO / "backtest" / "core" / "sol_1m_rsi_core.py"
PAPER = REPO / "scripts" / "sol_1m_rsi_core_paper.py"
DASH = REPO / "demo" / "rsi_1m_dashboard.py"
DAY_RT = REPO / "backtest" / "config" / "sol_day_runtime.yaml"
DAY_RES = REPO / "backtest" / "config" / "sol_day.yaml"
P_1M_STATE = REPO / "data" / "sol_1m_rsi_core_state.json"
P_DAY_SIG = REPO / "data" / "sol_day_latest_signal.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_lock() -> dict:
    return json.loads(LOCK_PATH.read_text())


def parse_assigns(path: Path) -> dict:
    tree = ast.parse(path.read_text())
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            tgt = node.targets[0]
            if isinstance(tgt, ast.Name):
                try:
                    out[tgt.id] = ast.literal_eval(node.value)
                except Exception:
                    pass
    return out


def yaml_simple(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line or line.startswith(" ") or ":" not in line:
            s = line.strip()
            if s.startswith("open_only_during_session:"):
                out["open_only_during_session"] = s.split(":", 1)[1].strip().lower() == "true"
            continue
        key, val = line.split(":", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if val == "":
            continue
        try:
            out[key] = ast.literal_eval(val)
        except Exception:
            out[key] = val
    return out


def check(name: str, got, want, issues: list[str]) -> dict:
    ok = got == want
    if not ok:
        issues.append(f"{name}: got {got!r} want {want!r}")
    return {"ok": ok, "got": got, "want": want}


def heartbeat(path: Path, max_age_s: int) -> dict:
    if not path.exists():
        return {"ok": False, "age_s": None, "note": "no file"}
    age = time.time() - path.stat().st_mtime
    return {"ok": age <= max_age_s, "age_s": int(age), "note": "fresh" if age <= max_age_s else "stale"}


def audit() -> dict:
    lock = load_lock()
    rsi_l = lock["rsi_1m"]
    day_l = lock["sol_day_v3"]
    issues: list[str] = []
    checks: dict = {}

    core = parse_assigns(CORE)
    mapping = {
        "rsi_period": "RSI_PERIOD",
        "atr_period": "ATR_PERIOD",
        "rsi_long": "RSI_LONG",
        "rsi_short": "RSI_SHORT",
        "stop_atr_mult": "STOP_ATR_MULT",
        "target_r": "TARGET_R",
        "risk_pct": "RISK_PCT",
        "daily_cap_r": "DAILY_CAP_R",
        "paper_equity_start": "PAPER_EQUITY_START",
    }
    for lock_key, const in mapping.items():
        got = core.get(const)
        want = rsi_l[lock_key]
        if isinstance(want, float):
            got = float(got) if got is not None else None
        checks[f"core.{const}"] = check(f"core.{const}", got, want, issues)

    hours = core.get("SESSION_HOURS_UTC")
    if isinstance(hours, (list, tuple)):
        hours = list(hours)
    checks["core.SESSION_HOURS_UTC"] = check("core.hours", hours, rsi_l["session_hours_utc"], issues)

    paper_txt = PAPER.read_text() if PAPER.exists() else ""
    imports_core = "from backtest.core.sol_1m_rsi_core import" in paper_txt
    redefines = bool(re.search(r"^RSI_LONG\s*=", paper_txt, re.M))
    checks["paper.imports_core"] = check("paper.imports_core", imports_core, True, issues)
    checks["paper.no_local_RSI_LONG"] = check("paper.no_local_RSI_LONG", redefines, False, issues)

    dash_txt = DASH.read_text() if DASH.exists() else ""
    dash_hours = re.search(r"SESSION_HOURS\s*=\s*\(([0-9, ]+)\)", dash_txt)
    if dash_hours:
        parsed = [int(x.strip()) for x in dash_hours.group(1).split(",") if x.strip()]
        checks["dash.hours"] = check("dash.hours", parsed, rsi_l["session_hours_utc"], issues)
    dash_long = re.search(r"RSI_LONG(?:\s*,\s*RSI_SHORT)?\s*=\s*([0-9.]+)", dash_txt)
    if dash_long:
        checks["dash.rsi_long"] = check("dash.rsi_long", float(dash_long.group(1)), float(rsi_l["rsi_long"]), issues)

    rt = yaml_simple(DAY_RT)
    res = yaml_simple(DAY_RES)
    for key in ("fvg_min_atr_multiple", "min_rr", "kelly_fraction"):
        if key in rt:
            checks[f"runtime.{key}"] = check(f"runtime.{key}", float(rt[key]), float(day_l[key]), issues)
    if "prefer_rr" in rt:
        checks["runtime.prefer_rr"] = check("runtime.prefer_rr", float(rt["prefer_rr"]), float(day_l["prefer_rr"]), issues)
    if "fvg_min_atr_multiple" in res:
        checks["research.fvg"] = check("research.fvg", float(res["fvg_min_atr_multiple"]), float(day_l["fvg_min_atr_multiple"]), issues)
    if rt.get("timeframe"):
        checks["runtime.timeframe"] = check("runtime.timeframe", str(rt["timeframe"]), day_l["timeframe"], issues)
    if "open_only_during_session" in rt:
        checks["runtime.session_hard_gate"] = check(
            "runtime.session_hard_gate", bool(rt["open_only_during_session"]), bool(day_l["open_only_during_session"]), issues
        )

    hb_1m = heartbeat(P_1M_STATE, 90)
    hb_15 = heartbeat(P_DAY_SIG, 300)
    status = {
        "ts_utc": utc_now(),
        "ok": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "checks": checks,
        "heartbeat": {"rsi_1m_state": hb_1m, "sol_day_signal": hb_15},
        "lock_file": str(LOCK_PATH),
    }
    return status


def write_status(status: dict) -> Path:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2, default=str))
    return STATUS_PATH


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=int, default=30)
    args = parser.parse_args()
    print("Formula lock agent")
    print(f"  lock={LOCK_PATH}")
    print(f"  status={STATUS_PATH}")
    while True:
        st = audit()
        write_status(st)
        mark = "LOCK OK" if st["ok"] else "DRIFT"
        print(f"[{st['ts_utc']}] {mark} issues={st['issue_count']} 1m_age={st['heartbeat']['rsi_1m_state'].get('age_s')} 15m_age={st['heartbeat']['sol_day_signal'].get('age_s')}")
        for item in st["issues"]:
            print(f"  - {item}")
        if args.once:
            sys.exit(0 if st["ok"] else 2)
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
