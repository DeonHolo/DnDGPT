# Actual summon runtime — development only

Summoning is an executable law attached to an owned source or item `Ability.program`, not inferred from its name or a `summoner` label. `summons.Manifest` declares the formation's actual templates, family, maximum active count, round duration or no encounter expiry, reject/replace-family policy and departure effects. Every `Unit` records actual HP/DEF/movement, resource pools, attributes, three-dimensional half extents, source-bound executable powers, control, utility, weaknesses and special-interaction descriptions. Those descriptions are not additional executable effects. No universal two-summon, tank/scout, copying, duration or command formula is imposed.

Creation now rejects a marked summoner candidate unless its actual kit contains a supported manifest program. All five offer/program and final-build checks apply. Test creation fixtures now include an actual autonomous manifestation instead of calling an ordinary attack a summoner. This is a structural/mechanical check, not proof of novelty, solo viability or rarity strength; semantic gates remain unfinished.

## Commands and phases

The existing default-off `enable_combat=True` switch enables these saved sandbox operations:

- `manifest_summons(actor_id, ability_id, placements)`: place exactly the declared formation, in template order, using `template_id` and an exact position per unit. Range, line of effect, actual body/solid occupancy and active caps are checked before costs or RNG. Only successful validation spends the source's declared Action/Free Action, MP/STA, item pools/stock, cooldown and use limits. IDs are server-generated from a monotonic saved sequence. Replacement removes only the owner's same-family units, with explicit receipts.
- `command_summons(actor_id, ability_id, orders)`: the owned command definition declares family, units per command, command range/line of effect, move/act permissions and whether both are allowed. Each order names a unique living owned commanded unit and a path and/or actual owned ability/targets. One shared owner activation can resolve several independently rolled unit attacks. Each unit still spends its own actual action/movement/resources/cooldown; another owner command cannot refresh it. Move OR act cannot silently become both.

Summons do not receive free entries in the main initiative order. Commanded creatures act only through actual permissions during their owner's turn. Autonomous creatures cannot be directly commanded; they follow their precommitted `WAIT` or `NEAREST_HOSTILE` behavior once at owner turn-end. The latter uses actual range/cover and a straight legal movement segment toward the nearest living hostile, with explicit move-only or move-and-act permission. A blocked route is held and recorded; there is no invisible repositioning or complete pathfinding claim. Unit passives, conditions, wards and renewable defensive Reactions use the shared resolver; Reaction policy is declared explicitly.

All orders receive a no-RNG preflight projection before the first real die. During execution, later conditional actions are checked again: if an earlier hit incapacitates a target or blocks a planned movement, that follow-up is skipped without spending the unit's unexecuted costs or drawing extra dice. The legal shared command itself remains spent. Actual failure before execution leaves the saved state untouched.

## Geometry, lifetime and saving

Each unit has its own position, footprint, movement spent and budgets. Moving bodies are checked against expanded solid bounds; a declared blocking creature also obstructs actual movement. Units do not gain passage-blocking, interception, sight blocking, flanking or infinite formation reach from prose alone. Regular actors retain the prototype's point-body representation; complete general body/terrain/area geometry remains unfinished.

Units reset budgets on the next owner turn. A duration of N rounds expires at the start of a turn in creation-round + N; no-duration units remain in this saved encounter. Destroyed, expired or replaced units leave the live roster with a departure receipt. The currently supported departure law is dismissal, including owner incapacitation. Persistent-after-owner-loss companions, triggered death/expiry effects, world-time expiry, recruitment and cross-encounter transfer require additional contexts and are not silently approximated.

The authoritative encounter, root summon projection, owner resources, unit resources/positions, command use, serial, deadlines and event commit in one existing owned approval transaction. Preview draws no dice and changes no real record. Concurrent approvals and retries/reopen return the same stored outcome and IDs. No extra inference API call is used.

Generated IDs skip existing actor identities instead of aliasing or failing a legal manifestation. If an active actor becomes incapacitated during an effect while other teams remain, initiative skips to the next living actor; declared owner-loss dismissal is applied before the next turn. The existing clock still accounts only for round boundaries/final partial rounds.

## Limits and evidence

This runtime supports bounded explicit formations and commands, narrow autonomous policies and the shared attack/save/effect system. Nested summoners, general programmable tactics, form networks/territories, multiple unit actions under earned special exceptions, full creature weaknesses/resistances, body-aware targeting/areas, all summoner evolutions and general companion agency remain unfinished. Limits of 32 templates per manifestation and 128 live units per development encounter bound work/payloads; exceeding them fails explicitly rather than being represented as a universal game rule. Full-game, playable creation and advancement flags remain false.

`tests/test_summons.py` covers contracts/roundtrip, four actual units, costs, preflight legality, individual reach, body collision, shared/independent command budgets, conditional follow-ups, autonomous behavior/obstructions, expiry, replacement, destruction/owner loss, cooldown and Reaction policy. `tests/test_summon_transactions.py` covers actual saved roster, scope/owner boundaries, pause, default-off behavior, concurrent commit, pending/reopened retries and signed HTTP/MCP. These use disposable fixtures, not real campaigns, live Chat, semantic certification or hosting acceptance.

Final-source 1.0.9 regression: **276 passed**, including **32 new summon cases**, two existing dependency warnings (`test-results/summon-final-suite.xml`). Earlier focused30 and edge85 receipts remain separate. The first full274 receipt predates the last identity and active-incapacitation corrections and is superseded by the final run.
