# Starting builds and character confirmation — development contract

The saved creation workflow now requires an approved starting loadout and executable selected source powers before character confirmation. It still defaults off, creates no playable campaign and does not advance fictional time. Complete tier/originality certification, full item mechanics and live creation acceptance remain unfinished.

## Preparation and confirmation

After the Background and remaining attributes are selected, `prepare_starting_build` accepts one typed `loadout`. It does not accept replacement powers, rolls, attributes or chosen sources. Programs must already belong to the selected Class, two Signatures and optional Title; the selected Background must already contain its executable Imprint on an actually owned parent. The exact pre-roll Class review and its committed history context are revalidated; legacy drafts without that evidence cannot silently backfill it after rarity is known. Narrative-only legacy powers remain readable but cannot be silently repaired or finalized through this command. See CLASS_PREPARATION.md.

The proposal is inert. App approval saves the loadout and exact derived preview as the next owned draft version through the existing transaction. It can be revised with another approved proposal before confirmation; any older confirmation then has a stale version. `confirm_character(confirmed=true)` requires that complete supported preview and freezes it. Loadout changes are unavailable after confirmation. Opening preparation and separate adventure authorization remain later gates and revalidate the build; none of these transitions rolls dice.

`starting_build` in the public preview includes selected source identities/rarities, all selected powers, attack bonuses and save DCs from the allocated attributes, the Imprint nested under its parent, current/max starting resources, equipment, individually tracked items, grouped supplies, funds and carried weight. It excludes raw rarity receipts, offer-certification assertions and private opening commitments. The existing private preparation fields remain separate.

## Gear-First loadout

- Exactly sixteen named equipment slots, each empty or referencing a real individual item. An equipped object's slots must exactly match one declared equip mode. Two-handed equipment is one object with one weight, referenced from both hands.
- Individually tracked items declare identity, rarity, per-piece grams, quantity, physical `EQUIPPED`/`CARRIED` location, acquisition provenance, equip modes, actual flat bonuses, requirements and incompatibilities. Only equipped functional items apply bonuses. Rarity never supplies an implicit modifier. Quantities cannot duplicate equipped objects.
- Supported flat bonuses affect HP/MP/STA maxima, DEF, movement and carrying capacity. Starting resources are calculated at their resulting maxima rather than accepted as arbitrary client values. Item powers use the same typed Ability contract and explicit pool costs; unsupported attribute/enchantment or untyped ability fields fail validation.
- Carry calculations use integer grams, include worn gear once, multiply individual-item quantity and add each supply category's aggregate bulk once. No mandatory eight-cell backpack, pocket or quick-reference puzzle is introduced. Over-capacity starting loadouts are rejected; containers/external storage and encumbrance movement rules remain later work.
- Grouped ordinary supplies record quantity, units, aggregate bulk and provenance. Funds use explicitly named local currency and provenance; no fixed denomination or free initial balance is assumed.
- Charges, battery and ammunition record exact current/maximum values, including zero. A typed ItemPower declares actual pool/quantity expenditure; no effect or refill is inferred. Borrowed items retain an explicit return obligation. Runtime retrieval/activation is described in ITEM_RUNTIME.md.
- Impaired starting gear cannot be equipped until an executable impairment rule exists. Worn/serviceable gear uses only its declared supported bonuses; no random wear roll occurs.

These structural checks do not certify physical plausibility, acquisition truth, creative novelty or rarity strength. `executable_programs_validated=true` means the selected source programs use supported operations; `semantic_tier_certification=false` remains explicit. Bounded item use, stock/pools, swaps and retrieval now execute in the development runtime. All-five offer certification, general item Reactions/triggers, world timers, attribute-changing gear, container limits, damage/repair, semantic compatibility and a player creation screen remain required for the full goal.

OFFER_VALIDATION.md describes the additional all-offer program gate: unsupported unselected options cannot pass final build transitions, old drafts remain inspectable and source/item power IDs must be distinct. Program validation does not close semantic rarity or originality certification.

## Evidence

`tests/test_starting_builds.py` covers calculations, DCs, parent-only nesting, confirmation freeze, strict decoding, illegal slots/ownership, two-hand accounting, rarity/unequipped non-bonuses, bulk/requirements, zero pools and loan obligations. `tests/test_starting_build_transport.py` runs the sequential workflow over signed HTTP/MCP fixtures, checks scope/owner boundaries, approves the exact preview once and confirms that no campaign/time or extra rarity draws occur. The repository transcript also recovers the pending build after reopening, retries one stored approval and preserves prior receipts. These are disposable development tests, not live Chat or real second-account acceptance.
