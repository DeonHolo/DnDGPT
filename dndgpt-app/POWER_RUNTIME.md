# Executable power runtime — development only

`app/powers.py` defines bounded immutable programs attached to the actual `abilities.Ability` (`creation.Ability` remains a compatible import); `app/combat.py` executes them. Item powers share that contract and bind to their actual owned item: see ITEM_RUNTIME.md. Novel names, themes and source identities remain generated. There is no fixed class catalogue, narrative-code interpreter, `eval`, arbitrary state patch or model API call. The complete edition 1.0 rule files are unchanged.

Enable only in a disposable development application with `create_app(..., enable_combat=True)` or `Engine(store, enable_combat=True)`. The flag requires an actual boolean, defaults off and has no environment switch. Production/default tools reject combat operations and omit them from dashboard capabilities. Full engine, playable creation and advancement-offer flags remain false.

## State and approval flow

1. Create a fresh paused development sandbox.
2. Propose `prepare_combat` with exact `actors`, `order` and `obstacles` fields. It creates an inert ready scenario once; player resources/attributes/derived statistics must match the authoritative character. Enemy definitions, powers, resistances, positions and turn order are then fixed. No preparation roll occurs.
3. Approve preparation, then separately approve `resume` and `start_combat`.
4. Propose `use_ability` with `actor_id`, `ability_id`, `target_ids`; `combat_move` with `actor_id`, a waypoint `path`; or `end_turn` with `actor_id`. Actual execution uses the existing app approval token, owner, expected version and action ID.
5. Each commit saves resource/budget/effect state, the original outcome receipt and the hash-chained event together. Concurrent confirmations and post-restart retries return the committed result. This is committed-action idempotency, not a promise that an uncommitted RNG draw survives a process crash.

Proposals validate every target and reserve only known costs in a disposable projection. They never draw dice or promise a random effect result. Invalid targets, prerequisites, resources, cooldowns and conflicting condition definitions fail before the first draw. An executed miss or successful enemy save still spends the declared MP/STA and activation budget. Unrelated sandbox mutations cannot change resources while an encounter is ready/active. Pause blocks gameplay.

## Supported bounded programs

- `Formula`: dice count/sides, flat amount and one relevant attribute modifier. Negative totals clamp to zero.
- `Resolution`: automatic effect, attack against actual DEF, or saving throw against the declared DC formula (default base 12 plus the casting modifier). Natural 20/1 checks are recorded. A critical attack adds one set of base damage dice; fixed bonuses and integrated rider dice are not doubled.
- `Effect`: damage, healing, MP/STA restoration, non-stacking temporary HP ward, a timed declared condition, or removal of one condition ID. Saves can explicitly halve damage; precommitted resistance ratios are exact 0, 1/2, 1 or 2. Healing/restoration caps at the existing maximum; no revival primitive exists.
- `Program`: relationship/count, attribute/condition prerequisites, per-turn/per-encounter uses and cooldown. A cooldown of N blocks the next N owner turns. Action and activated Free Action budgets are separate. Exact integer 3D range and solid-box cover apply; movement consumes the whole explicit path, rounding each segment up to a millimetre.
- `Condition`: bounded attack/DEF/movement modifiers and declared activation restrictions. IDs must have consistent definitions unless explicitly replaced. Refresh/replace/ignore and expiry are explicit. Durations count subsequent recipient turns; removal does not refund movement already lost this turn.
- Passive triggers: self effects at `TURN_START` or `TURN_END`, with no activation cost. Manual casting is rejected.
- Defensive Reaction: self ward on an actual internal `INCOMING_DAMAGE` trigger. The sandbox's committed `MITIGATE` policy can spend an available renewable Reaction; `CONSERVE`, unavailable resources/cooldown and limited encounter charges prevent automatic use. This deliberately narrow policy is not the full GM tactical judgment system.
- One Background Imprint attaches a `Rider` to an actually owned parent. It can follow parent success/execution but has no separate activation, cost, cooldown or charge pool. It never creates a standalone spell button.

Temporary HP absorbs damage before current HP and never becomes permanent HP. Incapacitation stops further damage rolls, and the encounter completes when only one living team remains. Completed rounds and the final partial round each account for six seconds exactly once; this runtime does not award victory XP or loot.

Program can also carry a typed summon manifestation or shared command law. These require explicit placement/orders through the summon operations rather than generic casting; unit powers reuse this same resolver. See SUMMON_RUNTIME.md. Ordinary effects remain strict; an empty effect tuple is valid only with an actual summon/command law.

## Boundaries

Narrative-only legacy powers still decode but cannot execute. A typed program proves only that these operations are executable; it does not certify the surrounding prose, novelty, rarity strength or a complete starting build. Semantic offer certification remains a separate gate. General reactions/triggers, summons, body volumes, difficult terrain, initiative generation, advanced targeting, all condition/injury families, full equipment/consumable contexts, rest, rewards, progression and world consequences remain incomplete. Bounded item use and gear-aware advancement are described in ITEM_RUNTIME.md. This adapter is not a playable regular-Chat release and has not been deployed or tested in live Chat.

Evidence: `tests/test_powers.py`, `tests/test_combat_transactions.py`, `test-results/power-runtime.xml`. Tests use disposable local states and signed-token fixtures; they do not touch a campaign or establish provider/second-account/hosting acceptance.
