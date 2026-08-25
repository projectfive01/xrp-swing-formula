# SOL Day — Micro-unit phase ($96 → $1000)

## Plan
- Start equity: **$96** (real, on Binance mainnet)
- No withdrawals until the bankroll reaches **$1000**
- Then switch to the original monthly $1000 unit + extract excess

## Risk (locked)
| Item | Value |
|------|--------|
| Equity unit | $96 |
| Quarter-Kelly | 4.5% → **~$4.32 risk per trade** |
| Hard cap | 5% → ~$4.80 |
| Daily loss halt | 8% → ~**-$7.68** then stop for the day |
| One trade at a time | Yes |
| Min RR | 1:3 |

## Min notional reality check
Binance SOLUSDT often requires ~$5 notional minimum. With ~$4.32 risk and a tight stop, size can fail min-notional. The live executor will error rather than oversize. If that happens often:
- Slightly wider structural stops (still 1R definition), or
- Temporarily use risk closer to 5% ($4.80) only — never raise above max_risk_pct

## API key (mainnet)
1. Binance app/web → Profile → **API Management**
2. Create API key
3. Enable **Enable Spot & Margin Trading** only
4. **Disable Withdrawals**
5. Optional but recommended: IP allowlist for your home/VPS IP
6. Put key/secret in local `.env` only

```
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
BINANCE_ENV=mainnet
BINANCE_LIVE=0
```

Smoke test (no orders):
```bash
python scripts/sol_day_live_smoke.py
```

Go live only when ready:
```bash
BINANCE_LIVE=1 python scripts/sol_day_ws_runner.py --live
```

## Kill switch
```bash
echo ON  > data/KILL_SWITCH.txt
echo OFF > data/KILL_SWITCH.txt
```

## After $1000
Set `equity_unit_usd: 1000` in `backtest/config/sol_day_runtime.yaml`, keep Quarter-Kelly, and resume the original extract-to-reserve rules.
