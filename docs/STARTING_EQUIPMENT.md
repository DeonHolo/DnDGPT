# Starting equipment formula

Version 1.0.38 replaces the fixed-role outfit from 1.0.37 with contextual, weighted equipment slots. The premium allocation can belong to any eligible slot.

## Budget and quality

| Class rarity | Total points | First item's base | Other three items' minimum |
|---|---:|---|---|
| Common | 12 | Common | Common |
| Uncommon | 24 | Uncommon | Uncommon |
| Rare | 48 | Rare | Uncommon |
| Epic | 96 | Epic | Rare |
| Legendary | 192 | Legendary | Epic |
| Unique | 320 | Legendary | Epic |

Item costs are Common **1**, Uncommon **3**, Rare **8**, Epic **20**, Legendary **50**, Unique **120**. These are design points, separate from gold, sale prices and ordinary loot. The numbers are initial balance settings, not evidence of a completed balance study.

Reserve **6** points for functional ordinary essentials, including a weapon/focus if needed. Generate four special items from the remaining allowance. The first receives the premium base in the table; the other three start at their listed minimum.

Before each quality roll:

1. Reserve the minimum cost of every remaining item.
2. If the next tier fits after that reserve, a genuine d100 of **1–20** promotes this item one tier; **21–100** retains its base. If it cannot fit, set promotion chance to zero before rolling.
3. For a Unique class's first item, use **1–75 Unique / 76–100 Legendary** instead.
4. Charge the actual tier's cost. Proceed to the next item with the remaining points.

For allocation index `i` (0–3), remaining allowance `R`, supporting floor cost `F`, and next-tier cost `C`, promotion is affordable when `C + (3 - i) * F <= R`. Start with `R = budget - 6`. Unused points expire.

Luck does not modify this starting-equipment draw. Ordinary loot retains its separate rarity/Luck procedure.

## Which slot receives each allocation

Before rolling, the GM sets weights using the actual selected class, background and established story:

- **1:** plausible; the default for every slot.
- **2:** a clear class fit OR story fit.
- **3:** both class and story fit.
- **0:** genuinely incompatible or explicitly excluded by the player.

At least four slots stay eligible, and at least one receives a justified weight above 1. These weights are recorded before any outfit roll. Ring 1 and Ring 2 are separate legal slots. The other slots are Head, Face, Neck, Shoulders, Chest, Arms, Hands, Main Hand, Off-Hand, Waist, Legs, Feet, Back and Artifact.

For each item's independently rolled quality, draw its slot with:

`P(slot) = slot weight / sum of weights of remaining slots`

Use a genuine integer draw over the total weight, in the canonical equipment-slot order. Remove the selected slot and repeat, so the four special items use distinct slots. A single remaining ticket is certain and needs no random call. The budget follows the selected slot: a Unique ring pays the same 120-point quality cost as a Unique chest item.

Example: Artifact and Ring 1 each have weight 3; Off-Hand and Chest each have weight 2; the twelve other slots remain at 1. Total weight is **22**. The premium item has a **3/22** chance of being the ring, **3/22** the artifact, **2/22** the off-hand item, **2/22** chest gear, and **1/22** each other slot. After one slot is drawn, remove its weight before the next draw.

## Effects and character story

The GM designs useful effects at the actual rolled item tier, for the actual selected class. Record each item's origin, appearance, weight, drawn slot, summary and full mechanics. The four effects should complement each other.

Established story facts influence the weights. The resulting equipment also informs the generated Your story: an unusual ring might connect to an established background, or a newly manifested chestplate might become part of the awakening scene. Preserve the player's authored history, beliefs and commitments. The player can revise the prose.

The single recorded draw includes weights, reasons, qualities, slots and costs. The final creation save checks both tier and slot. Retries recover the same receipt, including receipts from 1.0.37. Existing inventories are not automatically rerolled. This adds no approval, player-choice turn or routine gameplay tool call.
