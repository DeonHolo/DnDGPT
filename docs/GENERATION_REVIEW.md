# Generated class and ability review

On October 21, 2026, a read-only sample from the connected service contained two kits with 15 saved abilities and a third draft with no saved abilities. The empty draft was excluded rather than counted as a successful kit. No generation requests, rolls or campaign writes were made. Private campaign names, IDs and lore are excluded here; the local corpus and judgments remain in ignored `dndgpt-app/test-results/` files.

This is one qualitative review of saved text. It does not measure how often an ability gets used in play, prove originality, establish balance or test long-campaign continuity.

## What the sample shows

**Palimpsest Cantor:** the kit distinguishes damage/threshold denial, a defensive reroll, single-turn setup and observation. The integrated threshold upgrade inherits its parent's action. Its document and doorway Utilities remain narrow. The writing-disruption power's fallback mentions “pinched ink” without clearly stating its supply requirement away from writing.

**Tideglass Alchemist:** attack/stain payoff, selectable zones, temporary panels, pulling and reaction mitigation create different roles. Some saved rules are incomplete: Frostglass reduces movement without specifying the amount, and “maximum 2” stains does not specify whether the limit is per target or global. The saved kit also uses legacy AGI and measured ranges. The sample must not be presented as a complete current-rules example. Existing characters were left unchanged.

All 15 abilities were reviewed for their mechanical role, clarity and a specific supporting excerpt. The three identifiable Utility abilities were also judged against four ordinary situations:

| Saved Utility | Travel | Shelter / repairs | Information | Helping people |
| --- | --- | --- | --- | --- |
| Archive of Discrepancies | Unsupported | Unsupported | Conditional: physically revised writing within a month | Conditional: a relevant altered record exists |
| The Door That Remembers | Unsupported | Unsupported | Conditional: reachable doorway/hatch used within 24 hours | Conditional: tracing that recent passage |
| Assayer's Sight | Conditional: accessible terrain material | Conditional: material analysis only, no repair granted | Supported domain; exact knowledge/check still unclear | Conditional: an accessible ordinary sample |

“Conditional” means the written mechanics require a relevant circumstance; it does not count as an automatic success. “Unsupported” means the power grants no such effect. The wider material-analysis domain offers more ordinary applications, but needs a clear resolution rule. None of these judgments grants new permissions to a saved ability.

## Use this review for new offers

Keep a class's strong niche, but require its main Utility to support multiple ordinary situations without waiting for a bespoke clue or prop. State the common use, cost/time, outcome and limits. Check that a second Utility offers a different kind of help. Do not turn every Utility into a combat attack or a bonus to an ordinary skill check. Reject an offer with an undefined effect amount or trigger before presenting it as complete.

For each kit, compare what triggers a power, what the player does, what changes and how it is limited. Two different names or elements do not prove different mechanics. Read the whole kit for overlapping roles, missing quantities and dependencies that cannot be resolved from the saved text.

## Repeat the evaluation

Capture actual generated output read-only, with provenance and the full mechanical text. Review every sampled ability once, giving its role, clarity, finding and an exact source excerpt. For Utility, record `supported`, `conditional`, `unsupported` or `unclear` plus a reason for `travel`, `shelter_and_repairs`, `information` and `helping_people`.

Run `python -m scripts.evaluate_generation --corpus test-results/generated-corpus.json --review test-results/generated-review.json --output test-results/generated-quality.json` from `dndgpt-app`. The runner verifies complete coverage and that cited evidence occurs in the source. It reports 15 reviewed abilities and 12 scenario judgments for this sample. These are coverage counts, not quality scores. It rejects missing reviews, invented excerpts and explicitly synthetic provenance. Its unit fixtures test the evaluator; they are not generation evidence.

Future comparisons should include new offers generated under the revised rules, multiple reviewers and observed use during actual play. The current review identifies defects and supplies a repeatable rubric; it does not establish an improvement rate.
