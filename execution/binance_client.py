#!/usr/bin/env python3
"""
Minimal Binance Spot REST client (stdlib only).

Auth via env:
  BINANCE_API_KEY
  BINANCE_API_SECRET
  BINANCE_ENV = mainnet | demo | testnet  (default mainnet for funded accounts)

Never logs secrets.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class BinanceError(Exception):
    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"Binance HTTP {status}: {body[:500]}")


class BinanceSpot:
    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        env: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
        env = (env or os.environ.get("BINANCE_ENV", "mainnet")).lower()
        if env == "demo":
            self.base = "https://demo-api.binance.com"
        elif env == "testnet":
            self.base = "https://testnet.binance.vision"
        else:
            self.base = "https://api.binance.com"
            env = "mainnet"
        self.env = env

    def _sign(self, params: dict) -> str:
        query = urlencode(params, True)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        signed: bool = False,
    ) -> Any:
        params = dict(params or {})
        headers = {"User-Agent": "sol-day-exec/1.0"}
        if signed:
            if not self.api_key or not self.api_secret:
                raise BinanceError(0, "Missing BINANCE_API_KEY / BINANCE_API_SECRET")
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            params["signature"] = self._sign(params)
            headers["X-MBX-APIKEY"] = self.api_key

        qs = urlencode(params, True)
        url = f"{self.base}{path}"
        if method == "GET":
            if qs:
                url = f"{url}?{qs}"
            data = None
        else:
            data = qs.encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode())
        except HTTPError as e:
            body = e.read().decode(errors="replace")
            raise BinanceError(e.code, body) from e
        except URLError as e:
            raise BinanceError(0, str(e)) from e

    def ping(self) -> dict:
        return self._request("GET", "/api/v3/ping")

    def price(self, symbol: str) -> float:
        data = self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})
        return float(data["price"])

    def exchange_info(self, symbol: str) -> dict:
        data = self._request("GET", "/api/v3/exchangeInfo", {"symbol": symbol})
        return data["symbols"][0]

    def account(self) -> dict:
        return self._request("GET", "/api/v3/account", signed=True)

    def create_order(self, **params) -> dict:
        return self._request("POST", "/api/v3/order", params, signed=True)

    def cancel_order(
        self,
        symbol: str,
        order_id: int | None = None,
        orig_client_order_id: str | None = None,
    ) -> dict:
        p: dict = {"symbol": symbol}
        if order_id is not None:
            p["orderId"] = order_id
        if orig_client_order_id is not None:
            p["origClientOrderId"] = orig_client_order_id
        return self._request("DELETE", "/api/v3/order", p, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict:
        return self._request(
            "GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id}, signed=True
        )

    def open_orders(self, symbol: str | None = None) -> list:
        p = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/api/v3/openOrders", p, signed=True)


def round_step(qty: float, step: float) -> float:
    if step <= 0:
        return qty
    precision = max(
        0, len(str(step).rstrip("0").split(".")[-1]) if "." in str(step) else 0
    )
    return float(f"{qty - (qty % step):.{precision}f}")


def filters_for(symbol_info: dict) -> dict:
    out = {}
    for f in symbol_info.get("filters", []):
        out[f["filterType"]] = f
    return out
