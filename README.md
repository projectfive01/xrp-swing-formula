# XRP Swing Formula Research

Frozen **BASE** swing rules for XRP, plus a research store, paper-trading protocol, probability lab, formula brain flow, JSON Schema validation, and CI.

> Not financial advice. Small historical sample (n=6). Paper first.

## BASE formula (frozen)

1. **Exhaustion:** >=20% rise in <=10 days **and** daily RSI >= 75
2. **Entry:** first >=10% pullback from local high that still holds the 200-day area
3. **Exit:** ~7-10 trading days **or** daily close back under 200-day
4. **Size (hybrid):** risk ~1% equity; stop distance for sizing = min(2xATR%, 12%)
5. **Catalyst:** weight only (-1 / 0 / +1) — never opens a trade alone

**Action:** HOLD until load-bar progress = 100% (all gates green).

## Layout

```
docs/                 Protocols + one-pager
data/                 Research store (jsonl + variants)
labs/                 Interactive HTML tools
schemas/              JSON Schema contracts
scripts/              validate_store.py
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

## CI

On push/PR to main: validate JSONL + BASE freeze + path smoke checks.
