# Creation offer program validation — development only

Every one of the five Class, Signature, Title or Background offers must now use supported executable programs before `complete_board` can publish the board. A missing program in the fifth option blocks the whole completion, even if that option would not be selected. Existing source identity, rarity, duplicate-ID, native Free Action and owned-parent checks remain mandatory.

For Backgrounds, the exact rider is bound to the actually owned parent. A damage rider cannot attach to the runtime's ward-only defensive Reaction. No independent Imprint activation, cost, cooldown or pool is created. Unsupported mechanics must be implemented or corrected at the same fixed rolled rarity before publication; completion never rerolls candidates.

`public_preview.board_programs` reports each board's offer count, `programs_validated`, issue candidate IDs/details and `semantic_tier_certification=false`. These are derived diagnostics, not stored migrations. Old narrative-only drafts remain readable and retain their original bytes/receipts; missing programs are reported without auto-repairing owned powers. Preparing/finalizing a starting build and opening/adventure authorization revalidate all offered programs, including unselected legacy options. The normal read preview does not enforce that new transition gate retroactively.

The final starting preview also rejects duplicate IDs between selected source powers and actual item powers. A build that would collide in combat cannot be confirmed as ready.

Completion proposals and confirmations share the same checks. A rejected completion creates no proposal/event or board publication. Correcting that unpublished request can reuse its unconsumed action ID. Current-schema confirmations also revalidate older pending requests; unsupported old requests return structured `invalid_creation` errors before saving and leave their approval result unset. No automatic rewriting of displayed offers is introduced.

Program validation does **not** prove physical description agreement, conceptual originality, solo viability, tier strength or summoner completeness. The existing four prose certification fields are not an independent semantic oracle. A private 12–15-seed Class review is now structurally required before rolls; see CLASS_PREPARATION.md. The semantic correctness of that review, all-five tier/full-kit review, broader executable mechanics, the player creation UI, authorized campaign materialization and actual regular-Chat acceptance remain required. All development adapters and full-game capability flags retain their previous defaults.

The later summon runtime adds a structural check: a candidate marked `summoner` must contain a real supported manifestation, not an ordinary attack. New fixtures use actual autonomous units. General summoner variety, semantic completeness and rarity strength still require their full review; see SUMMON_RUNTIME.md.

Evidence: `tests/test_offer_programs.py` exercises every position across all four boards, actual Reaction-parent compatibility, read-only legacy diagnosis, final-gate bypass attempts, item/source ID collision and old pending approval rejection. `tests/test_starting_build_transport.py` rejects a fifth invalid option through both signed HTTP and MCP for every board, then completes at the same rolled grades and confirms a valid build. These are disposable local fixtures, not generated playable classes or live-Chat acceptance. No inference API client, live save mutation or publication is added.

The focused suite passed 34 tests; the full final-source 1.0.8 regression passed 244 tests with two existing dependency warnings. Reports: `test-results/offer-programs.xml`, `offer-full-suite.xml`.
