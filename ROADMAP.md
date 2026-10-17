# DnDGPT request tracker

Updated: 18 October 2026. Checkboxes mean implemented and checked in the working files; release status is recorded separately.

## ASAP — current approved work

- [x] Pull the latest GitHub README while preserving direct edits.
- [x] Archive the prior complete rulebook and Rule Hardener with integrity hashes; keep the gameplay-facing rulebook label at Version 1.0.
- [x] Add the Epic, Legendary and Unique class-skill guarantee to the complete rulebook.
- [x] Define Utility skills as class-native, flavor-locked, outside-combat abilities; guarantee 1 for Epic/Legendary and 2 for Unique.
- [x] Record the approved new-game HP/MP, rest and failed-check direction in the rulebook; keep the separate resource removed from the current rules text.
- [x] Update public README wording for hosted rule access, onboarding, ChatGPT usage expectations and voluntary PayPal support.
- [x] Implement and target-test the owner-scoped permanent campaign-delete tools: named preview, explicit confirmation, bounded resumable cleanup, Appwrite adapter cleanup and stale-retry protection.
- [ ] Review and release the documentation and deletion change; record local checks and hosted acceptance separately.
- [x] Apply current starting resources to new standard chat games: HP = 45 + 3 × STR; MP = 75 + 5 × INT. Preserve existing saves and explicit custom-rule builds.
- [x] Check class-native role counts before confirming a new standard character, including two Utilities for Unique.
- [x] Make independent Utility eligibility, rarity rolls and creativity/flavor checks explicit in both complete rules documents.
- [x] Replace skill dropdown stacks with a compact index and ability reader; add text highlights and retain full mechanics.
- [x] Give World an article index and Campaign Log a searchable timeline.
- [x] Add swappable dark atmospheres using credited public-domain paintings and a plain option.
- [x] Recheck the system's identity against its actual rules and primary sources; explain the system-hack description in the README.
- [x] Add desktop/mobile guidance and suggested thinking levels, including the current Pro-effort UI limitation.

## Future — migration and reliability

- [ ] Confirm the exact Appwrite Education expiry; choose a successor before it ends.
- [ ] Test Cloudflare Workers + D1 compatibility with disposable fixtures; compare Azure and Cloud Run.
- [ ] Consider an owned domain to reduce connection changes during provider migration.
- [ ] Rehearse an export/import migration preserving owners, IDs, history and retry receipts.
- [ ] Measure concurrent-player capacity and database/read costs before broader promotion.
- [ ] Add automatic test CI, routine backups and a tested restore procedure.
- [ ] Offer an explicit opt-in migration for older campaigns.
- [ ] Playtest short-rest recovery and defensive MP use.
- [ ] Explore a separate standard D&D 5e dashboard as a future side project: compare MCP data models and prototype character, spell and encounter views without replacing DnDGPT rules.
- [ ] Review candidate MCPs: [procload/dnd-mcp](https://github.com/procload/dnd-mcp) and [study-flamingo/gamemaster-mcp](https://github.com/study-flamingo/gamemaster-mcp).

## Deferred — broader product changes

- [ ] Add further executable adjudication of rest and context-dependent failed-check consequences; the GM currently follows the complete written rules.
- [ ] Improve descriptive choice cards.
- [ ] Reduce dashboard polling cost with lightweight change checks and adaptive refresh.
- [ ] Validate class-kit mechanical distinctness and power quality beyond recorded role counts.
- [ ] Consolidate duplicated GM/Rule Hardener guidance after checking rule coverage.
- [ ] Improve onboarding toward public-directory distribution when account/platform requirements permit.
- [ ] Consider group GM tools or a private rulebook library if players want them.
- [ ] Revisit paid features only if desired; current preference is voluntary GitHub support.

## Release status

The full run passed 388 tests and found two rule-pagination ordering regressions plus one temporary-database failure caused by overlapping test runs. Canonicalizing public campaign state fixes exact retry equality while preserving pagination metadata before long rule text. All three affected tests and current standard-rule/package checks now pass in an isolated focused run: 18 passed. The full suite was not repeated after that correction. Browser checks use disposable local fixtures and cover Utility routing, long metadata, keyboard tabs, timeline search, themes and narrow-screen overflow; tested text colors have a minimum 6.56:1 contrast on the reading surface. Existing player saves have only been inspected, not changed or deleted. Polling remains deferred. Release verification is pending the main-branch push.
