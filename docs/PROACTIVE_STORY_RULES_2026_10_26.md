# Proactive GM and conclusive obstacles — 1.0.50

The GM should bring developments into the campaign instead of only resolving the last command and printing another menu. This shared rule revision applies to Age of Convergence and Sovereign System. It changes future narration and pacing, with no migration of player saves.

## What changed

- **GM initiative:** introduce new threads, discoveries, opportunities and opposition grounded in the setting. NPCs pursue goals, enemies organize, allies bring news and earlier choices produce new situations. Show observable changes before asking for the next action.
- **A scene must develop:** by the end of a resolved scene or substantial authorized journey, introduce something that changes the situation or opens another direction. At real junctions, offer distinct pursuits where the fiction supports them. Continuing the current goal remains a valid choice.
- **Two decisions means two:** count committed approaches to the same minor blockage across renamed menus. The reply resolving the second approach must conclude the obstacle or close that route and expose a different pursuit. Another inspection, tool suggestion or key-search menu cannot renew the allowance. A player can still type an explicit action and have it resolved directly.
- **Failure remains real:** the ceiling grants no automatic unlock, loot, invented cost or forced combat. A minor optional chest cannot hold the entire campaign hostage. Genuine combat rounds and distinct major-quest milestones keep their normal rules.
- **Random events supplement story:** a no-event result ends that random check; ordinary consequences, due NPC plans and coherent leads can still develop. Keep genuine event checks on eligible transitions and preserve their results. No reroll or authored substitute for a rejected random incident.
- **Manage threads:** a new lead is not automatically an accepted quest. Preserve completed objectives, optional pursuits, plain language and the proper-name budget. Follow the campaign's focus/dialogue preference and the player's chosen quiet pace.
- **Keep normal turn cost:** use existing state, continuity notes and the ordinary batched save. No new model call, recurring audit, extra save or full-history read is required.

The previous continuity paragraph's blanket instruction not to invent an encounter was replaced with the applicable world-initiative and random-event rules. Meaningful player choices, geography, genuine rolls, pause and advancement freezes remain binding.

## Where the rules live

The full contract is in the existing **continuity** section, with aligned wording in Chapter **2**, Chapter **32** and Chapter **32A**. The compact hardener and rule index point normal scene writing to it. Both compiled game books and bundled references are synchronized. The reversible revision audit preserves unrelated rules.

The continuity section is **7,797 characters** and still returns in one tool page. Hardeners are **7,895** characters for Age and **7,946** for Sovereign, also one page each. These sections can be read once and cached; the GM does not need to load them every turn.

## Expected behavior examples

These are review cases, not a claim that a model completed a campaign test.

| Situation | Required response |
| --- | --- |
| Two approaches to a minor chest have failed | Conclude or close the route in that reply. Keep the contents unearned and offer a different pursuit. Resolve an explicit later player action without restarting the menu chain. |
| An eligible 30% event check rolls 53 | Keep no random event. Continue legitimate consequences or due NPC plans; do not replace the rejected event or reroll. |
| A scene has only answered small commands | Bring in a coherent discovery, actor move or opportunity that changes the available directions. |
| The player chose a conquest-focused campaign | Develop threats, scouting, rival deployments, territory and opportunities that fit that focus; follow its dialogue preference. |
| The player inspects the dashboard or is in frozen advancement | Do not advance clocks or commit new world action. |

## Verification

Focused rule routing, document integrity, compilation and event-engine checks: **49 passed**, with two existing dependency warnings. [Full release CI](https://github.com/DeonHolo/DnDGPT/actions/runs/40212099624): **659 passed** on runtime commit `6065f4d45925ca0b9f0dd0f18969768b1bb5ea62`. These checks cover document delivery and existing mechanics; they do not measure actual model narration or prove that every future GM reply follows the policy.

Public health reports **1.0.50**. Native MCP reads for both games return matching released rulebook/hardener hashes; the complete continuity contract and each hardener return with `next_offset=null`. Production deployment: `6ade2f911fba9e0e96e8`. Private probe deployment: `6ade2f8f16ce6c0084d6`. No player campaign was read or edited, and no plugin ZIP was uploaded.

For an ongoing chat, have the GM reload the latest **continuity** section and Chapter **2** once, then continue from the current save. This release does not reset the campaign or retroactively alter earlier chest attempts.
