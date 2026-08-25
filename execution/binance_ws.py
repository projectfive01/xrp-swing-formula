#!/usr/bin/env python3
"""
Binance Spot WebSocket helpers.

Env BINANCE_ENV:
  us | mainnet | demo | testnet
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable, Optional


def _ws_bases(env: str | None = None) -> tuple[str, str]:
    env = (env or os.environ.get("BINANCE_ENV", "us")).lower()
    if env in ("us", "binanceus", "binance.us"):
        return (
            "wss://stream.binance.us:9443",
            "https://api.binance.us",
        )
    if env == "mainnet":
        return (
            "wss://stream.binance.com:9443",
            "https://api.binance.com",
        )
    if env == "demo":
        return (
            "wss://demo-stream.binance.com:9443",
            "https://demo-api.binance.com",
        )
    return (
        "wss://stream.testnet.binance.vision",
        "https://testnet.binance.vision",
    )


class StreamCallbacks:
    def __init__(self):
        self.on_kline: Optional[Callable[[dict], None]] = None
        self.on_kline_closed: Optional[Callable[[dict], None]] = None
        self.on_trade: Optional[Callable[[dict], None]] = None
        self.on_book_ticker: Optional[Callable[[dict], None]] = None
        self.on_user: Optional[Callable[[dict], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None


def _dispatch_public(msg: dict, cb: StreamCallbacks) -> None:
    event = msg.get("e")
    if event == "kline":
        k = msg.get("k") or {}
        payload = {
            "symbol": msg.get("s"),
            "interval": k.get("i"),
            "open": float(k.get("o", 0)),
            "high": float(k.get("h", 0)),
            "low": float(k.get("l", 0)),
            "close": float(k.get("c", 0)),
            "volume": float(k.get("v", 0)),
            "is_closed": bool(k.get("x")),
            "start_ms": k.get("t"),
            "end_ms": k.get("T"),
            "raw": msg,
        }
        if cb.on_kline:
            cb.on_kline(payload)
        if payload["is_closed"] and cb.on_kline_closed:
            cb.on_kline_closed(payload)
    elif event == "trade":
        if cb.on_trade:
            cb.on_trade(
                {
                    "symbol": msg.get("s"),
                    "price": float(msg.get("p", 0)),
                    "qty": float(msg.get("q", 0)),
                    "time": msg.get("T"),
                    "is_buyer_maker": msg.get("m"),
                    "raw": msg,
                }
            )
    elif event == "24hrMiniTicker":
        if cb.on_book_ticker:
            cb.on_book_ticker(
                {
                    "symbol": msg.get("s"),
                    "close": float(msg.get("c", 0)),
                    "raw": msg,
                }
            )
    else:
        if "b" in msg and "a" in msg and "s" in msg and cb.on_book_ticker:
            cb.on_book_ticker(
                {
                    "symbol": msg.get("s"),
                    "bid": float(msg.get("b", 0)),
                    "ask": float(msg.get("a", 0)),
                    "raw": msg,
                }
            )


class BinancePublicStream:
    def __init__(
        self,
        streams: list[str],
        callbacks: StreamCallbacks | None = None,
        env: str | None = None,
    ):
        self.streams = [s.lower() for s in streams]
        self.cb = callbacks or StreamCallbacks()
        self.env = (env or os.environ.get("BINANCE_ENV", "us")).lower()
        self._ws_base, _ = _ws_bases(self.env)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ws = None
        self.last_price: float | None = None
        self.last_kline: dict | None = None

    def _url(self) -> str:
        if len(self.streams) == 1:
            return f"{self._ws_base}/ws/{self.streams[0]}"
        joined = "/".join(self.streams)
        return f"{self._ws_base}/stream?streams={joined}"

    def _on_message(self, _ws, message: str) -> None:
        try:
            data = json.loads(message)
            if "stream" in data and "data" in data:
                data = data["data"]
            _dispatch_public(data, self.cb)
            if data.get("e") == "trade":
                self.last_price = float(data.get("p", 0))
            elif data.get("e") == "kline":
                k = data.get("k") or {}
                self.last_price = float(k.get("c", 0))
                self.last_kline = data
            elif "c" in data and data.get("e") == "24hrMiniTicker":
                self.last_price = float(data.get("c", 0))
        except Exception as e:
            if self.cb.on_error:
                self.cb.on_error(e)

    def _on_error(self, _ws, error) -> None:
        if self.cb.on_error:
            self.cb.on_error(error if isinstance(error, Exception) else Exception(str(error)))

    def _on_open(self, _ws) -> None:
        if self.cb.on_connected:
            self.cb.on_connected()

    def _run_websocket_client(self) -> None:
        import websocket  # type: ignore

        while not self._stop.is_set():
            try:
                self._ws = websocket.WebSocketApp(
                    self._url(),
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_open=self._on_open,
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                if self.cb.on_error:
                    self.cb.on_error(e)
            if self._stop.is_set():
                break
            time.sleep(3)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        try:
            import websocket  # noqa: F401
        except ImportError as e:
            raise RuntimeError("pip install websocket-client") from e
        self._thread = threading.Thread(target=self._run_websocket_client, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass


class BinanceUserStream:
    def __init__(self, callbacks: StreamCallbacks | None = None, env: str | None = None):
        self.cb = callbacks or StreamCallbacks()
        self.env = (env or os.environ.get("BINANCE_ENV", "us")).lower()
        self._ws_base, self._rest_base = _ws_bases(self.env)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._keepalive: threading.Thread | None = None
        self._listen_key: str | None = None
        self._ws = None

    def _rest_key(self) -> tuple[str, str]:
        key = os.environ.get("BINANCE_API_KEY", "")
        secret = os.environ.get("BINANCE_API_SECRET", "")
        if not key:
            raise RuntimeError("BINANCE_API_KEY required for user stream")
        return key, secret

    def _create_listen_key(self) -> str:
        from urllib.request import Request, urlopen

        key, _ = self._rest_key()
        req = Request(
            f"{self._rest_base}/api/v3/userDataStream",
            method="POST",
            headers={"X-MBX-APIKEY": key, "User-Agent": "sol-day-ws/1.0"},
        )
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        return data["listenKey"]

    def _keepalive_listen_key(self) -> None:
        from urllib.request import Request, urlopen

        if not self._listen_key:
            return
        key, _ = self._rest_key()
        url = f"{self._rest_base}/api/v3/userDataStream?listenKey={self._listen_key}"
        req = Request(
            url,
            method="PUT",
            headers={"X-MBX-APIKEY": key, "User-Agent": "sol-day-ws/1.0"},
        )
        with urlopen(req, timeout=15) as r:
            r.read()

    def _keepalive_loop(self) -> None:
        while not self._stop.is_set():
            for _ in range(30 * 60):
                if self._stop.is_set():
                    return
                time.sleep(1)
            try:
                self._keepalive_listen_key()
            except Exception as e:
                if self.cb.on_error:
                    self.cb.on_error(e)

    def _on_message(self, _ws, message: str) -> None:
        try:
            data = json.loads(message)
            if self.cb.on_user:
                self.cb.on_user(data)
        except Exception as e:
            if self.cb.on_error:
                self.cb.on_error(e)

    def _run(self) -> None:
        import websocket  # type: ignore

        while not self._stop.is_set():
            try:
                self._listen_key = self._create_listen_key()
                url = f"{self._ws_base}/ws/{self._listen_key}"
                self._ws = websocket.WebSocketApp(
                    url,
                    on_message=self._on_message,
                    on_error=lambda ws, e: self.cb.on_error
                    and self.cb.on_error(e if isinstance(e, Exception) else Exception(str(e))),
                    on_open=lambda ws: self.cb.on_connected and self.cb.on_connected(),
                )
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                if self.cb.on_error:
                    self.cb.on_error(e)
            if self._stop.is_set():
                break
            time.sleep(3)

    def start(self) -> None:
        try:
            import websocket  # noqa: F401
        except ImportError as e:
            raise RuntimeError("pip install websocket-client") from e
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._keepalive = threading.Thread(target=self._keepalive_loop, daemon=True)
        self._thread.start()
        self._keepalive.start()

    def stop(self) -> None:
        self._stop.set()
        try:
            if self._ws:
                self._ws.close()
        except Exception:
            pass
