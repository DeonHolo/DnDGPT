# Attribute naming and cinematic distances

Status: DEX and cinematic presentation implemented for future standard campaigns. Existing characters retain their recorded builds and the underlying movement rules remain in force.

## AGI → DEX

Dexterity keeps the same checks, defenses and scaling previously assigned to Agility. This is a terminology change, with no stat rebalance.

The active attribute vocabulary is in `dndgpt-app/app/rules.py#ATTRIBUTES`. Character creation and validation consume it; the dashboard renders the saved attribute keys. The rulebook, hardener, creation screen, examples, tests and bundled rule references also need to agree.

Implementation:

1. DEX is canonical for new standard characters, preserving the existing meaning and numbers.
2. Legacy AGI input remains accepted; updates containing both keys are rejected. Existing saves keep their recorded key.
3. Historical snapshots, immutable roll receipts, audit hashes and archived rule editions remain intact. Existing-campaign conversion remains an optional future task.
4. Both complete documents use a reversible revision record, `dndgpt-app/rules/dexterity-and-cinematic-reach-2026-10-18.json`, and synchronized plugin references. Gameplay edition stays 1.0.

A global search-and-replace would damage archived evidence and miss the distinction between a visible label and a persisted key. A cosmetic DEX label alone would leave tools and saved JSON using AGI, so it should be described honestly if used as an interim step.

## Distances

The current rulebook already specifies named zones and **Engaged / Near / Far / Distant** for ordinary play. Its **Heroic Tactical Hybrid and Cinematic Positioning** section keeps exact distances privately for movement, range, areas and counterplay. A Near target is not automatically in range of every ability.

The dashboard and new-ability guidance apply that existing presentation consistently:

| What the player sees | What it means |
| --- | --- |
| Engaged | Inside the relevant creature's melee reach |
| Near | Reachable with an ordinary move along an open route |
| Far | Beyond that move; ranged powers or extra movement may reach it |
| Distant | Requires several moves or exceptional travel |
| Blocked / elevated / behind cover | A meaningful obstacle or targeting constraint |

New abilities record a short `range_display` and complete `mechanics_display` using descriptive reach, named zones and legal targets. Every cost, trigger, condition and consequence must survive that presentation. Canonical `mechanics` keeps exact measurements for private adjudication; an optional **Measured source** disclosure makes it inspectable. Evolutions must keep both copies synchronized. Older saved ability text is not automatically rewritten.

Movement remains tactical. The GM checks speed, routes, obstacles, melee reach, disengaging, forced movement, elevation, cover and area boundaries privately. A normal move covers the character's legal movement; **Dash costs the ordinary Action**. Near is relative to that creature's movement and does not make every target legal for every skill.

Action choices should explain what can be done: **Reach the archer with Dash**, **Strike the guard without moving**, or **Catch both raiders in the blast**. Exact distances enter normal narration only when requested or needed to explain a disputed ruling.

A genuinely band-based ruleset is a larger redesign. It needs explicit rules for movement between bands, Dash, melee reach, disengaging and opportunity attacks, ranged targeting, blast sizes, forced movement, flight, cover, teleports and independently positioned allies. Broad bands can erase the difference between short and long reach, make small pushes too powerful, or include too many targets in an area. Existing skills would need individual conversions and saved encounters would need an explicit migration.

The current release retains precise private adjudication. A fully band-based variant needs separate playtesting before replacing the distance engine.
