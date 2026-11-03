# Sovereign embodied play — 4 November 2026

User approved the full rulebook audit recommendations. Implement a consistent Sovereign book, arbitrary coherent bodies, mobile/bound/distributed play, close-up tactical scenes and lower administrative overhead. Keep four substantial powers, meaningful six-tier rarity, owner-based permanent growth and persistent consequences. The attached Bound Dominion prompt is design material, not authorization to start or rewrite a player campaign.

## Decisions

- User clarification: remove the guaranteed UNIQUE creation override. Normal independent rarity/Luck is the default. An explicit player prompt may request a scoped override. Native powers and all three foundations inherit the selected class's actual rarity; new completion checks accept all six grades.

- New saves carry `creation.sovereign_ruleset=sovereign-embodied-2026-11-04`. Existing saves remain under their recorded progression; publishing/reading does not migrate them.
- Default new progression is two personal refinements and two permanent Sovereign developments at creation and each gained level, matching the requested two-Sovereign-pick custom draft. Fourth-level major personal refinement remains. Optional `creation.sovereign_growth` (1..4 per starting/per-level track) is set before opening development choices; no repeated counter corrections. Existing saves retain 2 personal / 1 Sovereign awards unless the player explicitly changes future rates in chat. That request requires no approval proposal, preserves earned balances and works while paused.
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
- [x] Exercise new progression, immutable objectives and legacy future-rate changes. All 39 focused cases pass, including actual batched saves, idempotent retries, paused changes and portable restore.
- [x] Run responsive browser verification: 13/13 pass, all four layouts at 375/768/1100px; direct phone/desktop inspection also passed.
- [x] Publish through established Git/Appwrite flow and verify release.

The pre-existing change to docs/CONTINUITY_TESTS.md is outside this work and must not be staged or overwritten.

## Validation so far

The first browser pass passed 12/13 checks, including every layout at 375/768/1100px. Its equipment check used case-sensitive innerText for a CSS-uppercase slot label; inspection showed the actual installed relic and the three correct empty body sockets. The assertion now checks semantic textContent and detects unwanted human anatomy case-insensitively. A fresh complete run passed 13/13. Direct dashboard inspection at 375px and 1100px also confirmed readable cards, intact margins and no horizontal overflow. The preview uses disposable local campaigns only.

The ui-ux-pro-max disclosure search returned an unrelated heading result and no match on its narrower retry. General accessibility, responsive layout, 44px controls and progressive disclosure guidance are used as fallback; no database match is claimed.

The first isolated Linux release CI passed 767/769 tests, rules synchronization and the hosted-runtime import. Both failures were old fixtures mixing a new campaign marker/starting allowance with legacy prepared data. The cached-start fixture now supplies an actual body, preserves the new two-pick allowance and explicitly banks its unused gift. The legacy battle fixture persists its legacy creation profile as well as its army state. No runtime validation was weakened. Three additional local end-to-end save, paused-rate and portable-restore checks passed.

## Published verification

Runtime **1.2.0**, implementation `da5f0f2546d398c5ce081279e6d2d9e02708c592`. The [isolated release workflow](https://github.com/DeonHolo/DnDGPT/actions/runs/41724672920) and [main workflow](https://github.com/DeonHolo/DnDGPT/actions/runs/41725133774) passed all **772 tests**, rule synchronization, isolated hosted import and portable packaging. The focused Windows run passed 39 cases; its 457.70 seconds are local test execution, not a measurement of a gameplay turn. The website's Pages deployment also succeeded.

At **2026-11-03 21:54 UTC** (4 November in Singapore), public health reported 1.2.0. The served application dashboard matches the tested source after removing exactly one hosting-injected Cloudflare analytics script for comparison. The response and application hashes are separately recorded; no other source is excluded. OAuth metadata is correct, and anonymous campaign/MCP requests remain 401. The public website contains the updated mode description. Evidence: local `dndgpt-app/test-results/sovereign-embodied-public-1.2.0.json`.

The actual connected DnDGPT MCP returned the complete one-page hardener (7,825 characters), index (7,219) and body chapter (2,641), with matching tested source hashes. Book/index source: `20ac46c9cf1950f46abd2da03beae0ddf144829e4a209a2f9aec9270f39d0103`; hardener: `e12a11d94fe1051a6d0b765dccd0e6efe21da702050e509acacb0b8c7b998735`. Evidence: local `sovereign-embodied-native-1.2.0.json` and `sovereign-browser.json` under the same results directory.

No real campaign was opened, edited or migrated for verification. No plugin ZIP was uploaded. Browser checks used disposable local saves and a simulated host; they do not certify ChatGPT's live generated story UI. No model-turn speed or creative-quality result is claimed.
