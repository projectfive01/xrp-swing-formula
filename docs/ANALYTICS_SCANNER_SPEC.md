# XRP Formula Research Store & Continuous Analytics

## Goal
Data storage that is constantly scanned for analytics research.
Analytics confirm **outliers** and **co-formations** so the formula progresses only on evidence.

## Storage layout

| File | Purpose |
|------|---------|
| `data/market_snapshots.jsonl` | Price, RSI, EMA200, ATR%, volume, XRP/BTC |
| `data/gate_scans.jsonl` | Each load-bar evaluation (progress %, HOLD/BUY) |
| `data/signals.jsonl` | EXHAUSTION / ENTRY_VALID / INVALIDATION / EXIT |
| `data/trades.jsonl` | Paper/live trades per variant |
| `data/variants.json` | BASE + lab variants (frozen definitions) |
| `data/findings.jsonl` | Outliers, co-formations, warnings |
| `data/analytics_runs.jsonl` | Log of each analytics job |

## Scan cadence
1. **Gate scan** — every 4-12 hours or on demand
2. **Market snapshot** — same cadence
3. **Analytics pass** — daily (expectancy, outliers, co-formations)
4. **Weekly rollup** — progression nomination check

## Outlier rules
- Trade outlier: return beyond 2 sigma within variant
- Variant outlier: strong stats but n < 8 -> WATCH, do not promote

## Co-formation rules
>=2 of: structure, momentum cool, XRP/BTC hold, volume dry-up, catalyst+1 only if structure valid

## Progression gate
- closed n >= 10
- median ret > 0 out-of-sample
- majority of wins had co-formation
- no open HIGH severity findings
- human promote only; BASE never auto-rewrites
