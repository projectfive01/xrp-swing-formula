# SOL Day Trading Research

Day trading research system for SOL, using the same unit framework as XRP swing trades.

## Standard Unit Rules (shared with XRP Swing)

| Parameter         | Value                    |
|-------------------|--------------------------|
| **Unit Size**     | Fixed **$2,000** notional |
| **Max Loss**      | **1R**                   |
| **Take Profit 1** | **3R** (scale out)       |
| **Take Profit 2** | **5R**                   |

## Status

Scaffold only. Rules are not yet frozen.

Planned components (mirroring XRP structure):

- Frozen day-trading formula (to be defined)
- Research store (`data/`)
- Paper trading protocol
- Gate scanner + daily runner
- JSON Schema validation

## Next Steps

1. Define the core SOL day-trading setup (session, indicators, entry/exit logic)
2. Freeze the BASE day rules
3. Add paper trading + walk-forward validation
4. Connect to live daily/intraday data feed

All SOL day trades will use the identical **$2,000 unit / 1R risk / 3R–5R targets** model.
