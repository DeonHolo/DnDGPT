# Sovereign embodied play — 4 November 2026

User approved the full rulebook audit recommendations. Implement a consistent Sovereign book, arbitrary coherent bodies, mobile/bound/distributed play, close-up tactical scenes and lower administrative overhead. Keep four substantial powers, meaningful six-tier rarity, owner-based permanent growth and persistent consequences. The attached Bound Dominion prompt is design material, not authorization to start or rewrite a player campaign.

## Decisions

- User clarification: remove the guaranteed UNIQUE creation override. Normal independent rarity/Luck is the default. An explicit player prompt may request a scoped override. Native powers and all three foundations inherit the selected class's actual rarity; new completion checks accept all six grades.

- New saves carry `creation.sovereign_ruleset=sovereign-embodied-2026-11-04`. Existing saves remain under their recorded progression; publishing/reading does not migrate them.
- Default new progression is two personal refinements and two permanent Sovereign developments at creation and each gained level, matching the requested two-Sovereign-pick custom draft. Fourth-level major personal refinement remains. Optional `creation.sovereign_growth` (1..4 per starting/per-level track) is set before opening development choices; no repeated counter corrections. Existing saves retain 2 personal / 1 Sovereign awards.
- `creation.sovereign_body`: mobile/bound/distributed, form, description, primary_attribute, movement/manipulation/communication/perception/vulnerability and body-appropriate equipment labels. Bound cores record fixed core_location and zero ordinary movement. Four to sixteen actual equipment locations reuse stable internal slot IDs, preserving budget/ownership without showing nonexistent human anatomy.
- New `sovereignty.domain` holdings, zones, assets and finite encounters use the same batched save. Integration conditions/encounter objectives cannot move after publication. Core assets refer to character HP/DEF rather than duplicating health. Abstract army phases are explicitly fast resolution; focal combat uses ordinary real rolls and tactical saves.
- `spend_sovereign_evolution` accepts a list (single-object legacy accepted), including two developments on one owner in one atomic save. Preserve old children/rarity and actual owner effects. Permanent acquisition may unlock an active owner capability via permanent_unlock; it does not create a temporary player command.
- `sovereign_awards` may award kind=character to target_id=campaign ID, using normal XP/Vital Surge and one receipt per achievement. Commander/formation progression stays independent. Do not also manually add that award's XP.
- No new gameplay tool, per-unit lookup, AI judge or routine full-book read. Normal cache/roll batching/single save flow remains.

## Work status

- [x] Audit the complete existing book, hardener, draft and relevant backend.
- [x] Implement initial body, scene, growth and multi-development backend support.
- [x] Replace stale inherited Sovereign instructions and synchronize rule/index/reference copies.
- [x] Add body/territory/defense dashboard views and body-appropriate gear labels.
- [x] Exercise new progression, immutable objectives and legacy future-rate changes (34 new tests pass). The independent transport retry/atomic-failure case also passes outside the Windows sandbox.
- [ ] Run responsive browser verification and full checks.
- [ ] Publish through established Git/Appwrite flow and verify release, if checks pass.

The pre-existing change to docs/CONTINUITY_TESTS.md is outside this work and must not be staged or overwritten.

## Validation so far

The first browser pass passed 12/13 checks, including every layout at 375/768/1100px. Its equipment check used case-sensitive innerText for a CSS-uppercase slot label; inspection showed the actual installed relic and the three correct empty body sockets. The assertion now checks semantic textContent and detects unwanted human anatomy case-insensitively. A new complete browser run is required. The preview uses disposable local campaigns only.

The ui-ux-pro-max disclosure search returned an unrelated heading result and no match on its narrower retry. General accessibility, responsive layout, 44px controls and progressive disclosure guidance are used as fallback; no database match is claimed.
