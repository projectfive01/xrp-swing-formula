# SOL Day — Execution Path (Paper → Live)

## Current stack (emotion-free)

1. **Grok Automation** `SOL Day v3 Market Watch`  
   Hourly scan → writes `data/sol_day_latest_signal.json`

2. **Phone bot** `SOL Day Executor` (prompt in PHONE_BOT_PROMPT.md)  
   You open it and ask “check” → it reads the signal and gives exact order text

3. **Optional computer watcher** `scripts/sol_day_signal_watcher.py`  
   Polls the signal file and auto-logs paper trades to `data/sol_day_paper_trades.jsonl`

## Paper practice (now)
- Let the automation + phone bot run.
- When READY, either:
  - Manually place the paper order on the exchange UI using the bot’s numbers, **or**
  - Run the watcher on your computer:  
    `python scripts/sol_day_signal_watcher.py --live-url`
- Log every result. Recalculate Kelly after ~30 closed trades.

## Live (later)
Only after paper results match the backtest edge directionally:
- Add Binance API keys to a restricted environment (IP allowlist, no withdrawal).
- Extend the watcher with a `live` flag that places the sized limit order.
- Keep daily loss limit at ~8% of the unit and hard stop at 1R.

## Monthly reset
Always restart the active trading unit at $1000.  
Extract anything above your soft target into XRP swing reserve / living costs / long-term.
