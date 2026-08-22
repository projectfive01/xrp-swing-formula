# XRP Swing Formula Research + SOL Day Trading

Frozen **BASE** swing rules for XRP, plus a research store, paper-trading protocol, probability lab, formula brain flow, JSON Schema validation, and CI.

> Not financial advice. Small historical sample (n=6). Paper first.

## Standard Unit Rules (XRP Swing + SOL Day)

| Parameter         | Value                    |
|-------------------|--------------------------|
| **Unit Size**     | Fixed **$2,000** notional |
| **Max Loss**      | **1R**                   |
| **Take Profit 1** | **3R** (scale out)       |
| **Take Profit 2** | **5R**                   |

These unit rules apply to both XRP swing trades and SOL day trades.

## BASE formula (frozen) — XRP Swing

1. **Exhaustion:** >=20% rise in <=10 days **and** daily RSI >= 75
2. **Entry:** first >=10% pullback from local high that still holds the 200-day area
3. **Exit / Targets:**
   - Stop = 1R
   - TP1 = 3R
   - TP2 = 5R
   - Time fallback: ~7-10 trading days **or** daily close under 200-day
4. **Size:** Fixed $2,000 unit (1R risk)
5. **Catalyst:** weight only (-1 / 0 / +1) — never opens a trade alone

**Action:** HOLD until load-bar progress = 100% (all gates green).

## SOL Day Trading (Scaffold)

Layout for SOL day trading units is being added under `sol-day/`.

Planned structure:
```
sol-day/
  README.md                 # SOL day rules (to be frozen)
  docs/                     # Day trading protocol & one-pager
  data/                     # Separate research store for SOL
  schemas/                  # JSON schemas for SOL day trades
```

SOL day trades will also use the same **$2,000 unit / 1R / 3R / 5R** framework.

## Layout

```
docs/                 Protocols + one-pager
data/                 Research store (jsonl + variants)
labs/                 Interactive HTML tools
schemas/              JSON Schema contracts
scripts/              validate_store.py
sol-day/              SOL day trading research (new)
.github/workflows/    CI
```

## Quick start

```bash
python3 scripts/validate_store.py
```

Open in browser:
- `labs/formula_brain_flow.html` — information flow
- `labs/formula_probability_lab.html` — bootstrap histogram lab

## Lab variants (not auto-promoted)

- **BASE** — frozen primary
- **PB8** — pullback >= 8%
- **HOLD7** — 7-day hold
- **LOOSE** — 15%/10d · RSI >= 70

Progression: n>=10 closed out-of-sample, median > 0, co-formations, human review.

## Status (seeded)

- 6 historical BASE trades backfilled
- First live gate scan: HOLD (~50%; need $1.28-$1.35 zone)
- Findings: HIGH warning on small n
- Unit model updated to fixed $2,000 / 1R / 3R / 5R (2026-08-22)

## CI

On push/PR to main: validate JSONL + BASE freeze + path smoke checks.
