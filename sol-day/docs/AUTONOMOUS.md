# SOL Day v3 — Autonomous Paper System

## What runs without you

| Component | Role | Cadence |
|-----------|------|---------|
| **Grok Automation** `SOL Day v3 Market Watch` | Cloud scan + writes GitHub signal | Hourly (session window) |
| **`scripts/sol_day_autonomous_runner.py`** | Local/VPS brain: detect + open/manage paper + risk limits | Every 2 min (configurable) |
| **Kill switch** `data/KILL_SWITCH.txt` | `ON` = no new entries | Manual |
| **Daily loss limit** | −8% of unit on the **Chicago** calendar → halt new entries | Automatic |

## Start the autonomous paper loop

On any always-on machine (laptop left open, VPS, Raspberry Pi):

```bash
cd xrp-swing-formula
python scripts/sol_day_autonomous_runner.py
# or
python scripts/sol_day_autonomous_runner.py --poll 60
```

One-shot test:

```bash
python scripts/sol_day_autonomous_runner.py --once
```

## Kill switch

```bash
echo ON  > data/KILL_SWITCH.txt   # stop new paper entries
echo OFF > data/KILL_SWITCH.txt   # resume
```

## Config

`backtest/config/sol_day_runtime.yaml` — equity unit, Kelly %, daily loss limit, poll interval, freshness, max entry distance.

`backtest/config/sol_day.yaml` is the **backtest** lockfile. Editing it does not change the runner.

## Entry guards (anti-printer)

A READY signal is not an automatic fill. `try_open` also requires:

- Kill switch off and daily halt off
- No open ticket
- Setup fingerprint not already consumed today
- FVG bar age ≤ `signal_fresh_minutes` (else signal is WAIT)
- Mark not already through the stop or past 3R
- `|mark R vs FVG mid|` ≤ `max_entry_distance_r` (default 1.25R)

On open, on close, or on an already-resolved skip (through stop / past 3R), the setup id `direction:mid:fvg_idx` is written to `consumed_setups` in `data/sol_day_daily_state.json`. Same-cycle TP → reopen of the same FVG is blocked.

Daily state keys off `session.timezone` (America/Chicago), not UTC midnight.

## Files the runner owns

- `data/sol_day_latest_signal.json` — current READY/WAIT (local)
- `data/sol_day_open_trades.json` — open paper position
- `data/sol_day_paper_trades.jsonl` — closed paper history
- `data/sol_day_daily_state.json` — Chicago day P&amp;L, halt flag, consumed setups
- `data/KILL_SWITCH.txt` — emergency stop

## What is still NOT autonomous (by design)

- **Live exchange orders** — paper only until you explicitly add API keys and a live flag after 20–30 closed paper trades.
- **GitHub signal write from the runner** — the runner writes local files; the Grok automation still updates the public GitHub signal for the phone bot.

## Phone bot

Keep using **SOL Day Executor** for instant “check” status. It reads the GitHub signal that the Grok automation refreshes hourly; the runner is the higher-frequency paper executor.

## Path to live

1. Run autonomous paper for 20–30 closed trades.
2. `python scripts/sol_day_paper_tracker.py stats` — confirm edge directionally matches backtest.
3. Only then add a restricted Binance key + live module (separate change).
