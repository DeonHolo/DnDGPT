# Finite quests and more eventful travel

Discussion proposal, 2026-10-24. The quest interface and event-rate changes below are not implemented. The approved normal-rarity update is release 1.0.39: Common 20%, Uncommon 30%, Rare 25%, Epic 15%, Legendary 7%, Unique 3%, before existing Luck enhancement. Existing offers and outcomes remain recorded as issued. Starting equipment retains its separate allocation.

## What exists

Chapter 32 already requires attainable objectives, definite success/failure, chapter endings, substantial rewards, and planning budgets of about 1–3 meaningful scenes for quick quests and 3–6 for standard quests. The actual Quest Journal uses the generic record renderer. It shows saved fields and a status label, without a dedicated objective checklist, completion counter, separate System reward section or completed archive.

The proposed work needs both clearer quest records and a dedicated renderer. Restating the existing narrative rules alone will not provide those controls.

## A quest has an end

- Keep one stable record per quest and update it in place. Put the chronological account of events in World & Campaign Log.
- Show type, difficulty, current status, a short premise, a concrete finish condition, and a finite checklist of required objectives. Typical side quests need 1–4 meaningful objectives. Main quests contain chapters that can each finish and pay out.
- Each objective has a stable identity and Pending / In progress / Done / Blocked state. Quantified objectives can show actual progress, such as 2/3 recovered seals. Count required objectives separately from optional bonus objectives.
- All required conditions satisfied means Completed. Resolve rewards once and move the quest to a collapsible Completed archive. A new complication becomes a separate, linked follow-up; it does not reopen the finished quest or move its finish line.
- Alternative approaches satisfy the same goal when promised; they are not all mandatory chores. Failure, abandonment and explicit pauses have their own visible states. Preserve the existing two-decision ceiling on repeated obstacles.

The visible checklist reports saved outcomes. The player does not need to click a checkbox or approve a completion to make earned progress count.

## System rewards and contract payment

Use two separate sections:

**System reward:** committed XP, campaign currency, equipment/materials, or a class-growth reward granted for the stated achievement. Preview the actual package when the quest is issued. Scale it to the character's level, difficulty, effort and number of meaningful scenes. Substantial quests should offer a useful concrete payoff. Some major quests can precommit a Unique System reward independently of a random rarity roll.

**Contract payment:** the separate money, goods or favor promised by an NPC or faction. Record who owes it and the actual collection condition. A pending contract payment can remain collectible after the System quest has completed. Do not present the same payment twice under different labels.

Routine quests can pay XP and useful currency/supplies. Substantial quests can add build-relevant equipment. Hard quests and chapter finales can offer a premium payoff such as high-rarity gear or one free Skill Evolution credit. These are package-design guidelines, not automatic cumulative entitlements to every reward type.

An evolution credit is bankable and spent when the player wants. It funds one normal eligible Skill Evolution selection at zero Skill Point cost, using the ordinary five-offer board and current rarity/Luck rules. Preserve source rarity, existing upgrade nesting and standalone-passive eligibility. It grants no extra level, Attribute Point, Talent Point or milestone breakthrough. It should not force a new advancement menu into the completion scene.

Completion, objective states and reward settlement should fit in the existing single batched save. Stable quest/reward identities must prevent duplicate awards after retries or reloads. Existing quests need an evidence-based conversion; preserve actual progress and promised rewards.

## Example card

Illustrative hard side quest, not a real campaign award:

**The Glassback Hunt — Active · 1/2 required objectives**

- Done: Locate the marked Glassback.
- Pending: Defeat the marked Glassback.
- Optional bonus: Recover its crest undamaged.

**System reward:** 150 XP, 100 silver, one bankable Skill Evolution credit.

**Contract payment:** 40 silver from the hunters' guild upon delivery of the crest.

The quest completes when the marked creature is defeated. The optional crest condition and outstanding guild payment do not keep the System quest open. Example amounts need tuning against the campaign's level and economy before an actual quest is offered.

## Random-event review

Current trigger rates per eligible transition are 5% for safe inhabited activity, 20% ordinary travel/exploration, 30% dangerous frontier/contested territory and 40% intensely unstable regions. These are not checks per chat message. Combat rounds, menus, inspections, advancement and routine tiny actions do not each trigger checks.

After a successful trigger, category odds are Combat 30%, Opportunity/Discovery 25%, World/Faction 20%, Hazard 15%, Social/Unusual 10%. Severity odds are Minor 50%, Moderate 30%, Major 15%, Exceptional 5%. Events can have beneficial, harmful, neutral or mixed consequences. At the ordinary 20% trigger rate, a combat-category event has a 6% chance and a Major/Exceptional event a 4% chance per eligible check, before any inapplicable-pool outcome.

Suggested trigger rates for discussion:

| Context | Current | Proposed |
|---|---:|---:|
| Eligible safe inhabited activity | 5% | 10% |
| Ordinary travel/exploration | 20% | 30% |
| Dangerous frontier/contested territory | 30% | 50% |
| Intensely unstable region | 40% | 70% |

Retain the category/severity tables and one-check-per-transition rule. Reuse prepared regional possibilities. Simple events can resolve within the declared action; substantial ones can offer a choice. Keep existing quest objectives intact rather than converting each event into a compulsory detour.

ChatGPT currently identifies eligible transitions and requests their rolls; saving chat-led state does not automatically schedule an event check. Percentages alone cannot show whether a specific campaign missed checks. Retain transition identity, risk, roll, selected outcome or no-event reason in the same save, and audit those records when diagnosing a campaign.
