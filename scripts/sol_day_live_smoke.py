#!/usr/bin/env python3
"""
Smoke-test Binance connectivity (no orders by default).

  # load env then:
  python scripts/sol_day_live_smoke.py

With --place-test (TESTNET only recommended):
  places a tiny far-away limit and cancels it.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.binance_client import BinanceSpot, BinanceError


def load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--place-test", action="store_true", help="Place far limit then cancel (needs LIVE=1)")
    args = parser.parse_args()

    client = BinanceSpot()
    print(f"env={client.env} base={client.base}")
    print("ping:", client.ping())
    px = client.price("SOLUSDT")
    print(f"SOLUSDT price: {px}")

    if not client.api_key:
        print("No API key set — public endpoints only. Add .env for signed tests.")
        return

    try:
        acct = client.account()
        bals = [b for b in acct.get("balances", []) if float(b["free"]) or float(b["locked"])]
        print(f"account ok — non-zero balances: {len(bals)}")
        for b in bals[:10]:
            print(f"  {b['asset']}: free={b['free']} locked={b['locked']}")
    except BinanceError as e:
        print(f"account error: {e}")
        return

    if args.place_test:
        if os.environ.get("BINANCE_LIVE") != "1":
            print("Refusing --place-test without BINANCE_LIVE=1")
            return
        if client.env != "testnet":
            print("Refusing --place-test on mainnet. Switch BINANCE_ENV=testnet.")
            return
        # far limit buy that should not fill
        far = round(px * 0.5, 2)
        print(f"placing test LIMIT BUY qty=0.1 @ {far} then cancel...")
        order = client.create_order(
            symbol="SOLUSDT",
            side="BUY",
            type="LIMIT",
            timeInForce="GTC",
            quantity="0.1",
            price=str(far),
        )
        print("order:", order.get("orderId"), order.get("status"))
        cancel = client.cancel_order("SOLUSDT", order_id=order["orderId"])
        print("cancelled:", cancel.get("status"))


if __name__ == "__main__":
    main()
