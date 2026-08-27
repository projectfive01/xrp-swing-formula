# SOL 1m RSI-S CORE

**Status: FORMULA LOCKED** — 2026-08-27

This is a separate front from SOL Day v3 (ChoCh + FVG). Do not reuse
structural stops, Quality Score, or 15m session windows here.

## Formula

| Input | Rule |
|-------|------|
| Market | SOLUSDT |
| Timeframe | 1 minute |
| RSI | Wilder 14 on **closed** 1m closes |
| Long | closed RSI ≤ 20 |
| Short | closed RSI ≥ 80 |
| Stop (1R) | 1 × ATR(14) beyond entry |
| Target | 2R |
| Session | UTC hours **7, 10, 11, 20** only |
| Paper equity | $2,000 |
| Risk | 1.0% of equity per trade |
| Daily cap | 3.0R |
| Inventory | one position at a time |

## What was broken in the previous local runner

The process looked like the SOL Day paper trader because of plumbing, not because the RSI formula was being followed:

1. **Forming-bar RSI.** Live ticker was written into the last 1m close, so RSI jumped 20+ points at unchanged price (e.g. 38.4 → 15.5).
2. **Mid-bar signals.** Entries fired on a poll tick, not on a newly closed 1m candle.
3. **Binance.US timeouts.** `api.binance.us` read-timeouts left RSI stale for minutes.
4. **SOL Day naming/exits.** Stop-outs were labeled "Structural Stop" even though this formula has no structure layer.
5. **Session filter still applies.** Hours `[7, 10, 11, 20]` UTC are part of the locked formula. Outside those hours `sess=False` and the correct signal is WAIT.

## Runner behavior now

- `backtest/core/sol_1m_rsi_core.py` — frozen thresholds + Wilder RSI/ATR
- `scripts/sol_1m_rsi_core_paper.py` — paper loop
- `scripts/sol_1m_rsi_core_live.py` — paper by default; `--live` requires `BINANCE_LIVE=1` and keeps a $2 risk cap

RSI is only printed from the last **closed** 1m bar. Price for stop/target management can be the live ticker.

## Run

```bash
python scripts/sol_1m_rsi_core_paper.py
```

Kill switch: `echo ON > data/KILL_SWITCH.txt`
