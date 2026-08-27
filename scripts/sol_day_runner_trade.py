"""Signal writing, daily state, and paper/live trade management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from scripts.sol_day_runner_io import (
    append_jsonl,
    kill_on,
    load_json,
    now_iso,
    p,
    save_json,
    session_tz,
    trading_date,
)

LIVE_MODE = False


def setup_fingerprint(sig: dict) -> str | None:
    direction = sig.get("direction")
    zone = sig.get("entry_zone") or {}
    mid = zone.get("mid")
    if direction not in ("long", "short") or mid is None:
        return None
    fvg_idx = sig.get("fvg_idx")
    if fvg_idx is None:
        return f"{direction}:{float(mid):.4f}"
    return f"{direction}:{float(mid):.4f}:{int(fvg_idx)}"


def setup_age_minutes(sig: dict) -> float | None:
    raw = sig.get("fvg_ts_utc") or sig.get("choch_ts_utc")
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
        return delta.total_seconds() / 60.0
    except Exception:
        return None


def mark_unrealized_r(direction: str, entry: float, stop: float, price: float) -> float:
    r_value = abs(entry - stop)
    if r_value <= 0:
        return 0.0
    if direction == "long":
        return (price - entry) / r_value
    return (entry - price) / r_value


def write_signal(cfg: dict, setup: dict | None) -> dict:
    risk_usd = min(
        cfg["equity_unit_usd"] * cfg["kelly_fraction"],
        cfg["equity_unit_usd"] * cfg["max_risk_pct"],
    )
    if setup is None:
        sig = {
            "status": "WAIT",
            "ts_utc": now_iso(),
            "symbol": cfg["symbol"],
            "formula_version": "v3",
            "direction": None,
            "entry_zone": None,
            "stop": None,
            "target_3r": None,
            "target_4r": None,
            "atr_14": None,
            "risk_usd_quarter_kelly": round(risk_usd, 2),
            "equity_unit_usd": cfg["equity_unit_usd"],
            "fvg_idx": None,
            "choch_idx": None,
            "fvg_ts_utc": None,
            "choch_ts_utc": None,
            "setup_id": None,
            "setup_age_minutes": None,
            "skip_reason": None,
            "notes": "Autonomous runner: no qualifying setup",
        }
    else:
        zone = {
            "low": round(setup["fvg_bot"], 4),
            "high": round(setup["fvg_top"], 4),
            "mid": round(setup["entry"], 4),
        }
        sig = {
            "status": "READY",
            "ts_utc": now_iso(),
            "symbol": cfg["symbol"],
            "formula_version": "v3",
            "direction": setup["direction"],
            "entry_zone": zone,
            "stop": round(setup["stop"], 4),
            "target_3r": round(setup["target_3r"], 4),
            "target_4r": round(setup["target_4r"], 4),
            "atr_14": round(setup["atr"], 4),
            "risk_usd_quarter_kelly": round(risk_usd, 2),
            "equity_unit_usd": cfg["equity_unit_usd"],
            "fvg_idx": int(setup["fvg_idx"]),
            "choch_idx": int(setup["choch_idx"]),
            "fvg_ts_utc": setup.get("fvg_ts_utc"),
            "choch_ts_utc": setup.get("choch_ts_utc"),
            "setup_id": None,
            "setup_age_minutes": None,
            "skip_reason": None,
            "notes": "Autonomous runner READY",
        }
        sig["setup_id"] = setup_fingerprint(sig)
        age = setup_age_minutes(sig)
        sig["setup_age_minutes"] = None if age is None else round(age, 1)
        fresh_limit = float(cfg.get("signal_fresh_minutes", 90))
        if age is not None and age > fresh_limit:
            sig["status"] = "WAIT"
            sig["skip_reason"] = f"stale_fvg age={age:.0f}m>{fresh_limit:.0f}m"
            sig["notes"] = f"Setup found but stale ({sig['skip_reason']})"
    save_json(p("latest_signal", cfg), sig)
    return sig


def daily_state(cfg: dict) -> dict:
    path = p("daily_state", cfg)
    state = load_json(path, {})
    today = trading_date(cfg)
    if state.get("date") != today:
        state = {
            "date": today,
            "timezone": str(session_tz(cfg)),
            "realized_pnl_usd": 0.0,
            "halted": False,
            "consumed_setups": [],
        }
        save_json(path, state)
    state.setdefault("consumed_setups", [])
    state.setdefault("timezone", str(session_tz(cfg)))
    return state


def save_daily(cfg: dict, state: dict) -> None:
    save_json(p("daily_state", cfg), state)


def consume_setup(cfg: dict, fingerprint: str | None, reason: str) -> None:
    if not fingerprint:
        return
    state = daily_state(cfg)
    consumed = list(state.get("consumed_setups") or [])
    if fingerprint in consumed:
        return
    consumed.append(fingerprint)
    state["consumed_setups"] = consumed
    save_daily(cfg, state)
    print(f"  consumed setup {fingerprint} ({reason})")


def pnl_r(trade: dict, price: float) -> float:
    entry, r = trade["entry_px"], trade["r_value"]
    if trade["direction"] == "long":
        return (price - entry) / r
    return (entry - price) / r


def manage_open(cfg: dict, price: float) -> None:
    open_path = p("open_trades", cfg)
    trades = load_json(open_path, [])
    if not trades:
        return
    still = []
    for t in trades:
        ur = pnl_r(t, price)
        t["unrealized_r"] = round(ur, 3)
        t["mae_r"] = round(min(t.get("mae_r", 0.0), ur), 3)
        t["mfe_r"] = round(max(t.get("mfe_r", 0.0), ur), 3)
        t["updated_at"] = now_iso()

        hit_stop = (t["direction"] == "long" and price <= t["stop_px"]) or (
            t["direction"] == "short" and price >= t["stop_px"]
        )
        hit_tp4 = (t["direction"] == "long" and price >= t["tp4_px"]) or (
            t["direction"] == "short" and price <= t["tp4_px"]
        )
        hit_tp3 = (t["direction"] == "long" and price >= t["tp3_px"]) or (
            t["direction"] == "short" and price <= t["tp3_px"]
        )

        if hit_stop:
            close_trade(cfg, t, price, "stop_1R", -1.0)
        elif hit_tp4:
            close_trade(cfg, t, price, "tp4", 4.0)
        elif hit_tp3:
            close_trade(cfg, t, price, "tp3", 3.0)
        else:
            still.append(t)
            print(f"  OPEN {t['id'][:8]} {t['direction']} unreal={ur:.2f}R mode={t.get('mode', 'paper')}")
    save_json(open_path, still)


def close_trade(cfg: dict, trade: dict, price: float, reason: str, pr: float) -> None:
    trade["status"] = "STOPPED" if reason == "stop_1R" else "CLOSED"
    trade["exit_ts"] = now_iso()
    trade["exit_px"] = round(price, 4)
    trade["exit_reason"] = reason
    trade["pnl_r"] = round(pr, 3)
    trade["pnl_usd"] = round(pr * trade["risk_usd"], 2)
    trade["updated_at"] = now_iso()
    append_jsonl(p("closed_trades", cfg), trade)
    state = daily_state(cfg)
    state["realized_pnl_usd"] = round(state.get("realized_pnl_usd", 0.0) + trade["pnl_usd"], 2)
    limit = -cfg["equity_unit_usd"] * cfg["daily_loss_limit_pct"]
    if state["realized_pnl_usd"] <= limit:
        state["halted"] = True
        print(f"  !! Daily loss limit hit ({state['realized_pnl_usd']}). Halting new entries.")
    save_daily(cfg, state)
    consume_setup(cfg, trade.get("setup_id"), f"closed:{reason}")
    print(f"  CLOSED {trade['id'][:8]} {reason} pnl={trade['pnl_r']}R (${trade['pnl_usd']})")


def try_open(cfg: dict, sig: dict, price: float) -> None:
    if kill_on(cfg):
        print("  Kill switch ON — no new entries")
        return
    state = daily_state(cfg)
    if state.get("halted"):
        print("  Daily halt active — no new entries")
        return
    open_path = p("open_trades", cfg)
    if load_json(open_path, []):
        return
    if (sig.get("status") or "").upper() != "READY":
        if sig.get("skip_reason"):
            print(f"  skip open: {sig['skip_reason']}")
        return
    direction = sig.get("direction")
    zone = sig.get("entry_zone") or {}
    entry = zone.get("mid")
    stop = sig.get("stop")
    if entry is None or stop is None or direction not in ("long", "short"):
        return

    entry, stop = float(entry), float(stop)
    r_value = abs(entry - stop)
    if r_value <= 0:
        return

    fingerprint = sig.get("setup_id") or setup_fingerprint(sig)
    consumed = set(state.get("consumed_setups") or [])
    if fingerprint and fingerprint in consumed:
        print(f"  skip open: setup already consumed {fingerprint}")
        return

    ur = mark_unrealized_r(direction, entry, stop, price)
    max_dist = float(cfg.get("max_entry_distance_r", 1.25))
    if ur <= -1.0:
        print(f"  skip open: mark already through stop ({ur:.2f}R)")
        consume_setup(cfg, fingerprint, "already_stopped")
        return
    if ur >= 3.0:
        print(f"  skip open: mark already past 3R ({ur:.2f}R) — missed fill")
        consume_setup(cfg, fingerprint, "already_3r")
        return
    if abs(ur) > max_dist:
        print(f"  skip open: mark {ur:.2f}R from entry (max {max_dist}R)")
        return

    risk_usd = float(sig.get("risk_usd_quarter_kelly") or cfg["equity_unit_usd"] * cfg["kelly_fraction"])
    size_sol = risk_usd / r_value

    if direction == "long":
        tp3, tp4 = entry + 3 * r_value, entry + 4 * r_value
    else:
        tp3, tp4 = entry - 3 * r_value, entry - 4 * r_value

    live_meta = None
    mode = "paper"
    if LIVE_MODE:
        try:
            from execution.live_executor import place_entry_with_stop

            live_meta = place_entry_with_stop(
                symbol=cfg["symbol"],
                direction=direction,
                entry=entry,
                stop=stop,
                risk_usd=risk_usd,
                live=True,
            )
            mode = "live"
            if live_meta.get("qty"):
                size_sol = float(live_meta["qty"])
            print(f"  ★ LIVE orders placed env={live_meta.get('env')} qty={size_sol}")
            if live_meta.get("stop_error"):
                print(f"  ! stop order warning: {live_meta['stop_error']}")
        except Exception as e:
            print(f"  LIVE order failed — falling back to paper only: {e}")
            live_meta = {"error": str(e)}
            mode = "paper"

    trade = {
        "id": str(uuid.uuid4()),
        "status": "OPEN",
        "mode": mode,
        "direction": direction,
        "formula_version": "v3",
        "setup_id": fingerprint,
        "entry_ts": now_iso(),
        "exit_ts": None,
        "entry_px": round(entry, 4),
        "exit_px": None,
        "stop_px": round(stop, 4),
        "tp3_px": round(tp3, 4),
        "tp4_px": round(tp4, 4),
        "r_value": round(r_value, 6),
        "size_sol": round(size_sol, 4),
        "risk_usd": round(risk_usd, 2),
        "equity_unit_usd": cfg["equity_unit_usd"],
        "pnl_r": None,
        "pnl_usd": None,
        "mae_r": 0.0,
        "mfe_r": 0.0,
        "unrealized_r": round(ur, 3),
        "exit_reason": None,
        "signal_ts": sig.get("ts_utc"),
        "fvg_ts_utc": sig.get("fvg_ts_utc"),
        "notes": f"autonomous_{mode}",
        "live_meta": live_meta,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "mark_price_at_open": price,
    }
    save_json(open_path, [trade])
    consume_setup(cfg, fingerprint, "opened")
    print(
        f"  ★ OPENED {mode} {direction} entry={entry} stop={stop} "
        f"size={size_sol:.4f} SOL risk=${risk_usd} mark_r={ur:.2f}"
    )
