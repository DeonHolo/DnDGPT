# Equipment, item powers and consumables — development runtime

`abilities.Ability` is shared by selected source powers and `ITEM` powers. Creation still requires exact Class/Signature/Title provenance; an item cannot masquerade as one of those sources. `gear.ItemPower` binds an executable program to the actual item's ID and rarity, with explicit quantity, charge, battery and ammunition costs. No item effect is inferred from its name, prose or rarity. Supported item passives require actual equipment and no activation expenditure; item Reaction authorization windows remain unsupported and are rejected.

## Saved commands

The existing `enable_combat=True` development switch also enables inventory commands. The default app omits/rejects them; full-engine and playable-creation flags remain false. `prepare_loadout` can initialize one fresh paused sandbox only. It preserves current HP/MP/STA rather than refilling them. No existing campaign is imported or modified.

- `equip_item(actor_id, item_id, slots)`: reference a real owned item and a legal slot mode. Displaced gear is stowed as whole objects, including both references to a two-handed object. `unequip_item(actor_id, item_id)` stows that object. Outside combat, the item's declared preparation time advances the clock; during combat only hand gear is supported, with one interaction for a straightforward draw/stow or an Action for rearrangement. Body gear changes require preparation outside combat.
- `retrieve_item(actor_id, item_id)`: spend a combat Action to move a genuinely packed item to accessible carry; outside combat use its declared retrieval time. It does not activate the item or grant another Action. A free hand is required.
- `use_item(actor_id, item_id, ability_id, target_ids)`: validate the actual source, equipment/access, free hand if required for drawing, stock, pools, resource/action costs, prerequisites and every target before RNG. Accessible carried items spend their draw interaction as well as the declared activation. An executed miss still spends real item costs; an illegal activation spends none. The generic combat `use_ability` path enforces the same item checks and cannot bypass them.

Item programs use the existing attack/save/effect/critical/targeting pipeline. A whole consumed object leaves the ledger and clears its slot references; a stock stack decreases once. Grouped ordinary supplies require common effects with positive stock expenditure and reduce their aggregate bulk proportionately. Empty charge/battery/ammunition values remain explicit and never silently refill. Receipts record actual pool before/after values, quantity, ownership/provenance and any loan return obligation; consuming a loan item does not make that obligation disappear from history.

All mutations use the existing owned proposal, app approval, expected-version and idempotency transaction. Preview may project known stock/resource costs but never rolls. Actual result, item state, enemy/character projections and hash-chain event commit together. Concurrent confirmations and post-restart retries return the original JSON-normalized result.

## Statistics and turns

One gear-aware calculator now serves equipment changes and Attribute Point recalculation. Changing maxima clamps current resources only when necessary; it never refills them. The existing legitimate level-up Vital Surge still fills HP/MP using the actual equipped maxima and leaves STA unchanged. Equipped bonuses therefore survive advancement without granting a second refill.

Combat preserves total movement already spent during the owner turn. Consuming speed gear and equipping another object cannot restore movement already used; speed changes are bounded by the new speed minus the same cumulative distance. Item passives stop when their item is stowed.

Combat input limits accommodate the aggregate bonuses from all sixteen slots. A numeric-boundary fixture exercises those legal contract maxima through actual movement and rejects a one-millimetre overspend; it does not certify the fixture's rarity strength or plausibility.

Combat preparation takes the player's actual saved equipment; a supplied scenario cannot substitute/refill it. Opponents may precommit their own validated loadout. Outside combat, current support is self-targeted automatic immediate item effects without cooldown/per-encounter limits or temporary condition/ward timers. Other uses require a persistent combat/condition context and fail explicitly; an ephemeral context must not reset timers or lose conditions.

## Limits and evidence

Item Reactions, general triggers, absolute world/condition timers, containers/external storage, full impairment/repair, reloading/recharging, trade/loot/crafting and semantic rarity/tier certification remain unfinished. Starting builds can now contain supported item programs, but a complete all-five offer certification and player creation UI are still required. No live Chat deployment or real second-account item play has been tested.

Final 1.0.7 evidence: 26 focused item tests passed (`test-results/items.xml`); the full final-source regression passed 212 tests with two existing dependency warnings (`test-results/item-full-suite.xml`). The initial full run of 211 preceded the final aggregate-stat boundary correction and is superseded.


Tests: `test_item_runtime.py` covers costs, illegal uses, draw/retrieval, swapping, grouped medicine, passives, source ownership, movement cycles and loan receipts. `test_item_transactions.py` covers gear-aware advancement, current-vital preservation, real time/stock, concurrent/restart idempotency, scenario-substitution rejection and signed HTTP/MCP owner/scope boundaries. Data are disposable local fixtures. Complete rulebook and hardener bytes remain unchanged.
