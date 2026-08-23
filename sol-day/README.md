# SOL Day Trading Research

Day trading research system for SOL, using the **exact same unit framework** as XRP swing trades.

## Standard Unit Rules (shared)

| Parameter         | Value                      |
|-------------------|----------------------------|
| **Unit Size**     | Fixed **$2,000** notional  |
| **Max Loss**      | **1R**                     |
| **Take Profit 1** | **3R** (scale out)         |
| **Take Profit 2** | **5R**                     |

These rules are locked for both XRP Swing and SOL Day.

## Current Status

- **BASE formula FROZEN** (2026-08-23)
- Shared unit model applied
- Primary TF: 15-minute, long-only v1
- Paper-first discipline identical to XRP BASE
- Live gate scan + paper watch can now be extended to SOL Day

See `docs/FORMULA_ONEPAGER.md` for the exact frozen gates.

## Structure

```
sol-day/
├── README.md
├── docs/
│   └── FORMULA_ONEPAGER.md     # FROZEN BASE rules
├── data/                       # to be populated with scans & paper trades
├── schemas/                    # optional day-specific schemas later
└── scripts/                    # day scanner (future)
```

## Next Steps (post-freeze)

1. Extend live gate scan to also evaluate SOL Day readiness (same cadence as XRP)
2. Arm SOL paper_watch when first 100% load-bar appears
3. Paper 20–30 trades
4. Walk-forward + bootstrap validation
5. Only then consider lab variants (shorts, 5m, looser RSI)

All SOL day trades are managed by the same `scripts/paper_trader.py` engine.
