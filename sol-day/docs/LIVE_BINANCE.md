# SOL Day — Live Binance Setup (Testnet First)

## Safety rules (non-negotiable)

1. **Testnet first** — use https://testnet.binance.vision keys until the full flow is verified.
2. **API key permissions**: Enable **Spot & Margin Trading** only. **Disable Withdrawals**.
3. **IP allowlist** when using mainnet.
4. Keys live in **`.env` only** (gitignored). Never commit keys.
5. Live orders require **both**:
   - `BINANCE_LIVE=1` in the environment
   - explicit `--live` on the runner (when wired)
6. Kill switch + daily loss limit still apply.

## Setup

```bash
cd xrp-swing-formula
cp .env.example .env
# edit .env — paste TESTNET key/secret, BINANCE_ENV=testnet, BINANCE_LIVE=0
```

Get testnet keys: log into https://testnet.binance.vision (GitHub login) → API keys.

## Smoke test (no real risk)

```bash
python scripts/sol_day_live_smoke.py
```

Optional: place a far-away test order and cancel (testnet only):

```bash
BINANCE_LIVE=1 python scripts/sol_day_live_smoke.py --place-test
```

## What was implemented

| Module | Role |
|--------|------|
| `execution/binance_client.py` | Signed REST client (HMAC), testnet/mainnet |
| `execution/live_executor.py` | Size by Quarter-Kelly risk, LIMIT entry + STOP_LOSS_LIMIT |
| `scripts/sol_day_live_smoke.py` | Connectivity + optional cancel test |

## Wiring into the autonomous runner

The paper runner stays default. Live path:

1. Confirm paper stats after 20–30 trades.
2. Set `BINANCE_ENV=testnet`, verify smoke + a full paper-to-testnet entry cycle.
3. Only then set `BINANCE_ENV=mainnet` with a restricted key and small unit.

Live placement uses the same levels as the signal:
- quantity = risk_usd / |entry − stop| (lot-size rounded)
- LIMIT at entry mid
- STOP_LOSS_LIMIT at structural stop

## Mainnet checklist

- [ ] 20–30 closed paper trades reviewed (`sol_day_paper_tracker.py stats`)
- [ ] Testnet full cycle OK
- [ ] API key: trade only, no withdraw, IP restricted
- [ ] `BINANCE_ENV=mainnet`
- [ ] Start with same $1000 unit / 4.5% risk
- [ ] Kill switch file known and reachable
- [ ] Daily loss halt verified
