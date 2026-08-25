# SOL Day v3 — Signal Writer

**Purpose:** Emotion-free signal bus between the Grok automation and any execution layer (paper or live).

## Files

| File | Role |
|------|------|
| `data/sol_day_latest_signal.json` | Current state. Overwritten on every automation run. |
| `data/sol_day_signals.jsonl` | Append-only history of every READY (and optionally WAIT) signal. |
| `schemas/sol_day_signal.schema.json` | JSON Schema for validation. |

## Status Values
- `READY` — Hard requirements met (Structure + ChoCh + first FVG ≥ 0.6×ATR) and fill available. Execution layer may act.
- `WAIT` — No valid setup.

## Downstream Execution Pattern
1. Poll `data/sol_day_latest_signal.json` (or watch the repo via webhook).
2. When `status == "READY"` and the signal is fresh (ts_utc within last N minutes):
   - Size position with Quarter-Kelly: `risk_usd = equity_unit_usd * 0.045` (or live equity × 0.045).
   - Place limit/market order toward `entry_zone`, stop at `stop`, targets at `target_3r` / `target_4r`.
3. After fill or invalidation, mark the trade in `data/trades.jsonl` and ignore the same signal until a new READY appears.

## Automation
The Grok task **SOL Day v3 Market Watch** (`fd177ca0-f531-47a2-8ccb-594abb804584`) is instructed to update these files on every run.
