# SOL Day — Research Enhancements (LOCKED)

**Status: LOCKED** as of 2026-08-23  
These findings come from the Aug 19–22 sample analysis and quality scoring work. They are now official improvements to how we select and manage trades.

## 1. Quality Score Filter (Mandatory)

Every setup is scored 0–10 on:

- Structure Clarity (0–2)
- ChoCh Quality (0–2)
- FVG Quality (0–2)
- Location (0–2)
- Context / Confluence (0–2)

**Rule**: Only take setups with **Quality Score ≥ 8**.

This single filter is the highest-leverage improvement. It removed the weaker Aug 20–21 continuation (Score 6) while keeping the strong Aug 19 long (9) and Aug 22 short (10).

## 2. FVG Size Must Be Meaningful

Use ATR(14) on the 5-minute (Wilder smoothing).

- Strong FVG: ≥ 1.0 × ATR → 2 points
- Acceptable: ≥ 0.6 × ATR → 1 point
- Weak: < 0.6 × ATR → 0 points

Prefer the **first clean FVG** after the ChoCh. Late or already-mitigated FVGs are lower quality.

## 3. Selectivity Over Frequency

Target only **3–4 high-quality setups**.  
It is better to pass on average setups than to force trades. The quality score enforces this automatically.

## 4. Exit Priority (Priced-In Logic)

Primary exit trigger remains:

1. Opposite Change of Character (structure break against the position)

Secondary triggers (only if structure is still intact):
- Clear opposing FVG + rejection
- Measured move completion + failure
- Momentum exhaustion with structure weakening

Do **not** use fixed 3R/5R as the main exit method on high-quality runners. The Aug 19 example showed that fixed targets leave significant R on the table.

## 5. Management Standard

- Risk exactly 1R at entry
- Move stop to break-even once +1R is reached
- Then manage as a runner under the priced-in exit rules
- One trade at a time

## Summary of Impact

| Finding                        | Effect on Formula                          |
|--------------------------------|--------------------------------------------|
| Quality Score ≥ 8              | Strongly reduces overtrading               |
| ATR-based FVG size             | Removes weak, low-edge inefficiencies      |
| Prefer first FVG after ChoCh   | Improves entry location                    |
| Opposite ChoCh as primary exit | Captures full runner potential             |
| Strict selectivity             | Aligns with 3–4 high-quality setups goal   |

These rules are now active for all future paper trading and automation logic.
