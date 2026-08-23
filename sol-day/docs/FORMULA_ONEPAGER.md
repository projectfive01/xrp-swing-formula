# SOL Day Trading — Formula One-Pager (BASE — FROZEN)

> **Status: FROZEN** as of 2026-08-23  
> All trades use the shared unit model: **$2,000 unit / 1R risk / 3R + 5R targets**.  
> Paper first. Same discipline as XRP BASE.

## Session & Timeframe
- Primary timeframe: **15-minute**
- Session preference: New York (13:30–20:00 UTC) preferred for highest liquidity; rules apply 24h
- Direction for BASE v1: **Long only** (shorts will be a later lab variant)

## BASE Gates (all must be green → BUY / paper entry)

1. **Trend**  
   15m close > 20-EMA **and** 15m close > VWAP (session or daily)

2. **Pullback**  
   Within the last 6 × 15m bars, price touched or came within 0.3% of the 20-EMA or VWAP and then recovered

3. **Momentum / Trigger**  
   15m RSI(7) crossed above 45 from below **or** current 15m close breaks the high of the pullback bar

4. **Not chasing**  
   15m RSI(7) < 75 at the moment of trigger

5. **Stop definition (defines 1R)**  
   The closer of:  
   - Structural low of the last 5 × 15m bars, or  
   - Entry − 1.5 × ATR(14) on 15m

## Targets & Exit
- Stop = 1R (hard)
- TP1 = 3R (scale out)
- TP2 = 5R (final)
- Time fallback: end of current UTC day or 6 hours from entry, whichever comes first

## Size
- Fixed **$2,000** notional per unit
- Risk exactly **1R**

## Action
Load bar reaches 100% (all five gates green) → **BUY** (paper).  
Otherwise **HOLD**. No discretionary overrides.

## Notes
- Keep rules frozen. Paper 20–30 trades before any lab variants.
- Same paper trader engine (`scripts/paper_trader.py`) and unit model as XRP.
- Future variants (e.g. short side, 5m, looser RSI) stay off the critical path until n ≥ 10 closed out-of-sample.
