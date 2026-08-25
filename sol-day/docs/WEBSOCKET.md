# SOL Day — WebSocket Streaming

## Why
REST polling every 2 minutes is fine for detection, but stops/targets should react on ticks. WebSockets give:
- Real-time trade prices for mark-to-market
- Kline-close events to re-run the locked formula
- Optional user-data stream for live fill/cancel events

## Install

```bash
pip install -r requirements.txt
```

## Run (paper)

```bash
python scripts/sol_day_ws_runner.py
```

Streams:
- `solusdt@kline_15m` — formula re-check on candle close
- `solusdt@trade` — continuous stop / 3R / 4R management

## Run (live testnet)

```bash
# .env: BINANCE_ENV=testnet, keys set, BINANCE_LIVE=1
BINANCE_LIVE=1 python scripts/sol_day_ws_runner.py --live
```

Also opens the **user data stream** (listenKey) for `executionReport` events.

## Module

`execution/binance_ws.py`
- `BinancePublicStream` — multiplex public streams, auto-reconnect
- `BinanceUserStream` — listenKey + 30m keepalive
- `StreamCallbacks` — on_kline, on_kline_closed, on_trade, on_user, on_error

## Architecture

```
Binance WS ── trade ticks ──► manage_open (stops/targets)
         └── kline close ──► detect_setup → signal → try_open
REST (seed / history) ──────► 300×15m klines for ChoCh/FVG structure
```

Structure detection still uses REST history (needs lookback). Streaming handles timing and risk exits.

## Env

| Variable | Purpose |
|----------|---------|
| `BINANCE_ENV` | `testnet` (default) or `mainnet` |
| `BINANCE_API_KEY` | Required for user stream / live |
| `BINANCE_API_SECRET` | Required for live orders |
| `BINANCE_LIVE` | Must be `1` with `--live` |
