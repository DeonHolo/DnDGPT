# DnDGPT request tracker

Updated: 17 October 2026. Checkboxes mean implemented and checked in the working files; release status is recorded separately.

## ASAP — current approved work

- [x] Pull the latest GitHub README while preserving direct edits.
- [x] Archive the prior complete rulebook and Rule Hardener with integrity hashes; keep the gameplay-facing rulebook label at Version 1.0.
- [x] Add the Epic, Legendary and Unique class-skill guarantee to the complete rulebook.
- [x] Define Utility skills as class-native, flavor-locked, outside-combat abilities; guarantee 1 for Epic/Legendary and 2 for Unique.
- [x] Record the approved new-game HP/MP, rest and failed-check direction in the rulebook; keep the separate resource removed from the current rules text.
- [x] Update public README wording for hosted rule access, onboarding, ChatGPT usage expectations and voluntary PayPal support.
- [x] Implement and target-test the owner-scoped permanent campaign-delete tools: named preview, explicit confirmation, bounded resumable cleanup, Appwrite adapter cleanup and stale-retry protection.
- [ ] Review and release the documentation and deletion change; record local checks and hosted acceptance separately.

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

- [ ] Apply the new-game resource and failed-check model to runtime validation and the dashboard.
- [x] Compact skill abilities into expandable rows with rarity, activation, status and applicable cost; keep mechanics expandable and Utility-labelled abilities in the Utility tab.
- [ ] Improve descriptive choice cards.
- [ ] Reduce dashboard polling cost with lightweight change checks and adaptive refresh.
- [ ] Enforce class-kit guarantees in character creation and runtime validation.
- [ ] Consolidate duplicated GM/Rule Hardener guidance after checking rule coverage.
- [ ] Improve onboarding toward public-directory distribution when account/platform requirements permit.
- [ ] Consider group GM tools or a private rulebook library if players want them.
- [ ] Revisit paid features only if desired; current preference is voluntary GitHub support.

## Release status

The revised rulebook, README, compact skill rows and campaign-delete workflow are implemented. The focused rule, package, MCP, SQLite and Appwrite regression set passes (41 tests). The earlier full run found three rule-integrity/package-sync failures; those were corrected and their affected tests now pass. A full-suite rerun was not repeated after the fixes. Nothing has been deployed or released, and no existing campaign was selected or deleted. Polling and broader resource/runtime changes remain deferred.
