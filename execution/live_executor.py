#!/usr/bin/env python3
"""
SOL Day live order helpers.

Safety:
  - Requires BINANCE_LIVE=1 AND explicit live=True
  - Defaults to testnet
  - Sizes with Quarter-Kelly risk $ / stop distance
  - Places LIMIT entry + STOP_LOSS_LIMIT protective stop when possible
"""

from __future__ import annotations

import math
import os
from typing import Any

from execution.binance_client import BinanceSpot, BinanceError, filters_for, round_step


def live_enabled() -> bool:
    return os.environ.get("BINANCE_LIVE", "0").strip() == "1"


def assert_live_allowed(live: bool) -> None:
    if not live:
        raise RuntimeError("live flag is False — paper only")
    if not live_enabled():
        raise RuntimeError("Set BINANCE_LIVE=1 in environment to allow live orders")


def client_from_env() -> BinanceSpot:
    return BinanceSpot()


def compute_qty(symbol: str, entry: float, stop: float, risk_usd: float, client: BinanceSpot) -> float:
    info = client.exchange_info(symbol)
    fl = filters_for(info)
    lot = fl.get("LOT_SIZE") or fl.get("MARKET_LOT_SIZE") or {}
    step = float(lot.get("stepSize", "0.001"))
    min_qty = float(lot.get("minQty", "0.001"))
    risk_per_unit = abs(entry - stop)
    if risk_per_unit <= 0:
        raise ValueError("invalid stop distance")
    raw = risk_usd / risk_per_unit
    qty = round_step(raw, step)
    if qty < min_qty:
        raise ValueError(f"qty {qty} below minQty {min_qty} — risk too small or stop too wide")
    # notional filter
    notional = fl.get("NOTIONAL") or fl.get("MIN_NOTIONAL") or {}
    min_notional = float(notional.get("minNotional", notional.get("notional", 5)))
    if qty * entry < min_notional:
        # bump to min notional if still within ~1.25x risk budget
        need = min_notional / entry
        qty2 = round_step(need, step)
        if qty2 * abs(entry - stop) > risk_usd * 1.25:
            raise ValueError("cannot meet min notional without exceeding risk budget")
        qty = max(qty, qty2)
    return qty


def place_entry_with_stop(
    *,
    symbol: str,
    direction: str,
    entry: float,
    stop: float,
    risk_usd: float,
    client: BinanceSpot | None = None,
    live: bool = False,
) -> dict[str, Any]:
    """
    Place limit entry near entry mid and a protective stop.
    direction: long | short
    """
    assert_live_allowed(live)
    client = client or client_from_env()
    side = "BUY" if direction == "long" else "SELL"
    stop_side = "SELL" if direction == "long" else "BUY"

    qty = compute_qty(symbol, entry, stop, risk_usd, client)
    info = client.exchange_info(symbol)
    fl = filters_for(info)
    price_filter = fl.get("PRICE_FILTER") or {}
    tick = float(price_filter.get("tickSize", "0.01"))
    entry_px = round_step(entry, tick)
    stop_px = round_step(stop, tick)

    # Limit entry
    entry_order = client.create_order(
        symbol=symbol,
        side=side,
        type="LIMIT",
        timeInForce="GTC",
        quantity=f"{qty}",
        price=f"{entry_px}",
    )

    stop_order = None
    stop_error = None
    try:
        # STOP_LOSS_LIMIT: stopPrice triggers, limit price slightly worse
        if direction == "long":
            limit_stop = round_step(stop_px * 0.999, tick)  # slightly below stop
        else:
            limit_stop = round_step(stop_px * 1.001, tick)
        stop_order = client.create_order(
            symbol=symbol,
            side=stop_side,
            type="STOP_LOSS_LIMIT",
            timeInForce="GTC",
            quantity=f"{qty}",
            price=f"{limit_stop}",
            stopPrice=f"{stop_px}",
        )
    except BinanceError as e:
        stop_error = str(e)

    return {
        "env": client.env,
        "qty": qty,
        "entry_px": entry_px,
        "stop_px": stop_px,
        "entry_order": entry_order,
        "stop_order": stop_order,
        "stop_error": stop_error,
    }


def cancel_all(symbol: str, client: BinanceSpot | None = None, live: bool = False) -> list:
    assert_live_allowed(live)
    client = client or client_from_env()
    open_orders = client.open_orders(symbol)
    results = []
    for o in open_orders:
        results.append(client.cancel_order(symbol, order_id=o["orderId"]))
    return results
