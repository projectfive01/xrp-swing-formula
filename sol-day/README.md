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

- Scaffold created
- Shared unit model applied
- Initial one-pager written (`docs/FORMULA_ONEPAGER.md`)
- **Rules not yet frozen**

## Planned Structure

```
sol-day/
├── README.md
├── docs/
│   ├── FORMULA_ONEPAGER.md
│   └── PAPER_TRADING_PROTOCOL.md   (can inherit from root)
├── data/                           # separate research store later
├── schemas/
└── scripts/                         # day scanner + paper trader
```

## Next Steps to Freeze a BASE Day Formula

1. Decide primary timeframe (5m / 15m)
2. Define exact entry gates (trend + momentum + trigger)
3. Define how 1R stop is calculated (structure vs ATR)
4. Paper trade the rules for 20–30 trades
5. Run walk-forward validation
6. Freeze the BASE day version

Once frozen, SOL day trades will be managed by the same `scripts/paper_trader.py` engine using $2,000 units / 1R / 3R / 5R.
