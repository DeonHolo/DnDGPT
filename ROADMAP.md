# DnDGPT request tracker

Updated: 18 October 2026. Checkboxes mean implemented and checked in the working files; release status is recorded separately.

## ASAP — current approved work

- [x] Give the player-facing FAQ its own README section and top navigation link.
- [x] Apply descriptive reach to the first power reveal, summon stats, commands, Full rules and upgrades; counted paces/steps are measurements too. Preserve exact source mechanics privately.
- [x] Derive companion names from individual identity and accessible naming records, with honest limits on cross-chat comparisons.
- [x] Pull the latest GitHub README while preserving direct edits.
- [x] Archive the prior complete rulebook and Rule Hardener with integrity hashes; keep the gameplay-facing rulebook label at Version 1.0.
- [x] Add the Epic, Legendary and Unique class-skill guarantee to the complete rulebook.
- [x] Define Utility skills as class-native, flavor-locked, outside-combat abilities; guarantee 1 for Epic/Legendary and 2 for Unique.
- [x] Record the approved new-game HP/MP, rest and failed-check direction in the rulebook; keep the separate resource removed from the current rules text.
- [x] Update public README wording for hosted rule access, onboarding, ChatGPT usage expectations and voluntary PayPal support.
- [x] Implement and target-test the owner-scoped permanent campaign-delete tools: named preview, explicit confirmation, bounded resumable cleanup, Appwrite adapter cleanup and stale-retry protection.
- [x] Release the documentation, campaign-delete tools and current runtime/UI changes; record local checks and hosted acceptance separately.
- [x] Apply current starting resources to new standard chat games: HP = 45 + 3 × STR; MP = 75 + 5 × INT. Preserve existing saves and explicit custom-rule builds.
- [x] Check class-native role counts before confirming a new standard character, including two Utilities for Unique.
- [x] Make independent Utility eligibility, rarity rolls and creativity/flavor checks explicit in both complete rules documents.
- [x] Replace skill dropdown stacks with a compact index and ability reader; add text highlights and retain full mechanics.
- [x] Give World an article index and Campaign Log a searchable timeline.
- [x] Add swappable dark atmospheres using credited public-domain paintings and a plain option.
- [x] Recheck the system's identity against its actual rules and primary sources; explain the system-hack description in the README.
- [x] Add desktop/mobile guidance and suggested thinking levels, including the current Pro-effort UI limitation.
- [x] Add MIT software licensing, CC BY 4.0 original-content licensing and third-party art exclusions; include license notices in release archives.
- [x] Restore the original dark green default as Classic, with Quiet Ink immediately underneath it; expand the dropdown to 33 atmospheres with selected-work credits.
- [x] Add twenty character-free fantasy environments from additional artists; exclude modern farms, industry and modern cities after visual review.
- [x] Add comfortable development-control padding and compact, initially collapsed connection/development disclosures.
- [x] Refresh the README's current-interface screenshots and explain the optional backgrounds.
- [x] Make the GM prefer hosted rules and check bundled copies against backend source before packaging.
- [x] Add GitHub test/document checks and a portable plugin ZIP artifact; document the separate authenticated ChatGPT package release step.
- [x] Review the writing-skill repository and strengthen semantic class variety, naming, player-perspective critique and narrative craft in both complete rule documents.
- [x] Require the World Preview to explain Convergence history, Earth's relevance and the character's open origin before the existing Luck gate.
- [x] Use 5e Hack and homebrew together in public descriptions; remove search-summary commentary from the terminology document.
- [x] Use DEX for new standard campaigns, preserve legacy attribute input, and synchronize the complete rulebook and bundled references.
- [x] Show descriptive skill reach and complete readable mechanics while retaining private movement and targeting checks; see [attribute and distance details](docs/ATTRIBUTE_AND_DISTANCE_OPTIONS.md).
- [x] Verify refreshed Cloud Dashboard metadata references the current hosted template; an already mounted chat view still needs reopening.
- [x] Release the visible campaign-deletion flow, separate Upgrades tab and dashboard-build diagnostic.
- [ ] Verify the plugin listing displays the dice icon after publishing its light/dark icon variants.

## Future — migration and reliability

- [ ] Confirm the exact Appwrite Education expiry; choose a successor before it ends.
- [ ] Test Cloudflare Workers + D1 compatibility with disposable fixtures; compare Azure and Cloud Run.
- [ ] Consider an owned domain to reduce connection changes during provider migration.
- [ ] Rehearse an export/import migration preserving owners, IDs, history and retry receipts.
- [ ] Measure concurrent-player capacity and database/read costs before broader promotion.
- [ ] Add routine backups and a tested restore procedure; consider gating deployment on the new CI checks.
- [ ] Offer an explicit opt-in migration for older campaigns.
- [ ] Playtest short-rest recovery and defensive MP use.
- [ ] Explore a separate standard D&D 5e dashboard as a future side project: compare MCP data models and prototype character, spell and encounter views without replacing DnDGPT rules.
- [ ] Review candidate MCPs: [procload/dnd-mcp](https://github.com/procload/dnd-mcp) and [study-flamingo/gamemaster-mcp](https://github.com/study-flamingo/gamemaster-mcp).

## Deferred — broader product changes

- [ ] Playtest fully band-based distances if desired; cinematic proximity with precise private adjudication is already implemented.
- [ ] Add further executable adjudication of rest and context-dependent failed-check consequences; the GM currently follows the complete written rules.
- [ ] Improve descriptive choice cards.
- [ ] Reduce dashboard polling cost with lightweight change checks and adaptive refresh.
- [ ] Validate class-kit mechanical distinctness and power quality beyond recorded role counts.
- [ ] Consolidate duplicated GM/Rule Hardener guidance after checking rule coverage.
- [ ] Improve onboarding toward public-directory distribution when account/platform requirements permit.
- [ ] Consider group GM tools or a private rulebook library if players want them.
- [ ] Revisit paid features only if desired; current preference is voluntary GitHub support.

## Release status

### Native event and action cards — 19 October 2026

Both complete books now carry the same polished native-card contract: genuine clickable choices, original non-emoji iconography, crisp hierarchy, purposeful accessible accents and concise consequential cost/risk lines. It uses Slay the Spire's event-screen readability as inspiration. Offer counts, action legality, confirmation gates, mechanics and saved outcomes are preserved; restyling never replays an action. The GM skill and presentation guide reinforce this preference. Exact native layouts remain controlled by ChatGPT.

**Published and verified:** [source 089d568](https://github.com/DeonHolo/DnDGPT/commit/089d56864ee3dc1ab9f5de2ff2b9999ebe7a8e3b) is active in Appwrite deployment `6ad58204b3e133a13906`. [GitHub CI](https://github.com/DeonHolo/DnDGPT/actions/runs/39190709346) passed **405 tests** and built the portable release; the focused local source, standard-rule and packaging suite passed **18 tests**. The existing private plugin is **1.0.27**. Its downloaded installed archive matches the canonical rulebook, hardener, GM skill and presentation bytes exactly; identity, App binding, metadata, audience and default prompt are preserved. The text source reader normalizes the hardener's line endings, so the archive was used for byte verification.

Authenticated hosted `read_rules` returns rulebook SHA-256 `b8c403b61bcf204021043a5448ab2392b14557ff7149eabb37aae76889d47113` and hardener SHA-256 `49dc3b8fe3f2b14e18cd44711116d063a16e90ada550bc2749f0bc1d7de6fa18`, matching source and the installed archive. The additive `polished-intelligent-ui-2026-10-19.json` revision proves all unrelated source bytes are unchanged. A direct anonymous health probe from the local terminal returned HTTP 403; this record relies on deployment metadata and authenticated rule reads, not a successful anonymous health check. Native generated-card appearance was not re-playtested for this instruction-only release. No campaign was created, advanced or modified.

### Player-facing details

Application **1.0.21** and plugin **1.0.26** curate player-facing facts instead of rendering arbitrary saved fields. Empty costs and cooldowns, parent IDs, preparation codes, internal flags and duplicate mechanics copies are hidden. Damage, HP, DEF, duration, real costs/cooldowns, depleted resources and meaningful counterplay remain. Upgrades prefer an explicit change summary and filter copied parent sentences in legacy entries. Five attributes use a balanced responsive layout. The complete rulebook, Rule Hardener and GM skill reinforce this writing contract through an additive, reversible source amendment.

Disposable local Chromium checks passed **12 cases**, including upgrade deltas already present in combined parent rules, zero HP/charges, readable companions/world records, 375/700/1100-pixel layouts and no input or saved-game mutation. The focused local source, standard-rule, server, packaging and atmosphere suite passed **41 tests**; canonical plugin references match. The self-contained dashboard is 940,263 bytes.

**Published and verified:** [source 8912adb](https://github.com/DeonHolo/DnDGPT/commit/8912adbe036e6fa3181f36e2925ad7909d2fdb95) is active in Appwrite deployment `6ad446c449d15b7ee59f`; health reports 1.0.21 and hosted HTML contains the exact player projection and upgrade renderer. [GitHub CI](https://github.com/DeonHolo/DnDGPT/actions/runs/39096186979) passed **405 tests** and built the portable release. The existing private plugin is **1.0.26**. Both complete books, the GM skill and presentation guide in its downloaded installed archive match source bytes; its App binding, identity, presentation and default prompt are preserved. Hosted `read_rules` returns the current canonical rulebook SHA-256 `07f5bad95acfe1a9d2da1e84dfafb908a8830c67fbca1c893e18c77cb0f588d4` and hardener SHA-256 `aa38b171360bbeb04784fac3197a96d3b246446749cf2888aed2ea8e4170f2cb`.

Browser rendering was checked locally with disposable fixtures, not in the actual ChatGPT client. A mounted dashboard still needs reopening, and an ongoing GM chat should read the current complete documents. These checks verify delivery and presentation; they do not guarantee every future model response. No player campaign was started, changed or deleted.

### Readable power reveals and FAQ

Application **1.0.20** and plugin **1.0.25** reinforce descriptive reach from the first creation offer, including inline kits, summon movement/attacks/commands, Full rules and upgrades. Counted paces/steps are measurements too. Exact source distances and movement limits remain private; nonspatial stats and mechanical restrictions are preserved. Companion naming follows individual identity and genuinely accessible history. FAQ is now a standalone README section linked from the top navigation.

**Published and verified:** [source faa1ae2](https://github.com/DeonHolo/DnDGPT/commit/faa1ae213b8faa0c31e7f99f83a8c3cd2623dcac) is active in Appwrite deployment `6ad4250e37fa51cde28f`; health reports 1.0.20. [GitHub CI](https://github.com/DeonHolo/DnDGPT/actions/runs/39087715762) passed **405 tests** and built plugin 1.0.25. The focused local source, standard-rule, server and packaging suite passed **32 tests**. The existing private plugin's page shows 1.0.25; downloading its installed ZIP verified both complete documents and GM skill against source, with its App binding and default prompt preserved. Rulebook SHA-256 is `35de9e975f8ea6fd22c53f315df19c27eb33de2960a02f97d0086de4e38f9f7e`; hardener SHA-256 is `de2fc110ff41c9eb6a7ae499448435cde6609a31ad4000b7b4af7979ce43616d`.

These checks verify delivery and source preservation, not every future model response. Existing chats should read the current complete documents and use readable descriptions; old messages are historical and saved mechanics remain intact. No live campaign was started or modified for this release.

### Atmospheres and upgrade reader

Application 1.0.19 and plugin 1.0.24 contain the 33-choice catalog, Classic rename, separate Upgrades tab, visible campaign-deletion confirmation and DEX/readable-reach guidance. The focused local suite passed 129 tests; the complete local suite passed **405 tests**. Browser checks used disposable local data: all 33 choices switched, only Classic and Quiet Ink had no artwork, the ability reader fit a 375-pixel viewport, and both disclosures started collapsed. Development controls had 17-pixel left and bottom insets. Deletion previews required the exact name and cancellation retained the fixture. No player campaign was changed or deleted.

The self-contained dashboard is 934,444 bytes with 31 AVIF images; its provenance manifest verifies asset hashes and licenses. The README count is checked against the actual catalog. Current screenshots show the Classic surface and a fantasy atmosphere with the Upgrades tab. Gameplay edition remains 1.0; source archives record the DEX amendment.

**Published and verified:** [source d6b49ec](https://github.com/DeonHolo/DnDGPT/commit/d6b49ec4fd7d8f421e8fcb5086e111be91973139) is live in Appwrite deployment `6ad41b1ad79245f83c91`; health and the authenticated dashboard tool report 1.0.19. Hosted HTML contains all 33 choices, with Classic and Quiet Ink first. [GitHub CI](https://github.com/DeonHolo/DnDGPT/actions/runs/39085125614) passed and built the portable ZIP. The existing private plugin was updated through **Upload new version**, and its page shows 1.0.24. Downloading that installed ZIP proved both complete rules match canonical source and the App binding/default prompt are preserved.

Refreshing **DnDGPT Cloud Dashboard** tools returned HTTP 200. The connector metadata now references `ui://dndgpt/dashboard-v1.0-1f5ab6edf84c.html`, matching the new local template hash. This verifies metadata selection; it does not replace an old mounted dashboard or prove a new campaign's generation quality. Players should reopen the view and read current rules. Server updates are shared by connected players; independently uploaded ZIP copies require their own package update.

### Previous release

The full local suite passed **394 tests** in an isolated run. After the final world-introduction insertion, new invalid-theme cases and package updates, the focused source/rules/theme/package run passed **26 tests**. Integrity tests reverse both new insertions and prove unrelated source text is preserved. Rules edition stays 1.0; application 1.0.18 and plugin package 1.0.23 carry these changes.

Browser checks used disposable local data: all thirteen atmosphere selections and credits worked, the 375-pixel view had no horizontal overflow, both Utilities routed correctly, connection details started collapsed, and development controls had 17-pixel left/bottom insets. Two current screenshots are in the README; the older ChatGPT integration capture is explicitly labeled. The self-contained dashboard resource remains below 1 MiB. No player campaign was changed or deleted. Polling remains deferred.

Backend Git deployments and installed plugin releases are separate. The older 1.0.21 installed package retained obsolete rules after the hosted service changed; 1.0.22 corrected that and made hosted reads take precedence. The new CI checks reference synchronization and builds a portable ZIP. Verify Appwrite deployment, hosted hashes, plugin source read-back and actual ChatGPT rendering separately; a local browser pass alone does not prove host acceptance.

**Verified release:** [main source 1f7ba93](https://github.com/DeonHolo/DnDGPT/commit/1f7ba93980c68af552958022872cedd246e28d81) is live on Appwrite as application 1.0.18. Authenticated `read_rules` hashes match both current source documents. Plugin 1.0.23 was uploaded and read back with both amendments and its existing connection unchanged; ChatGPT's plugin page shows that version. The corrected [GitHub CI run](https://github.com/DeonHolo/DnDGPT/actions/runs/39081226468) passed **400 tests** and uploaded its portable ZIP. The first CI attempt exposed a missing test-directory parent in a fresh checkout; the workflow now creates it.

**Open appearance issue:** the dice PNG and matching light/dark listing/composer fields are present in the released package, but the checked ChatGPT plugin page still displays its generic icon after reload. The listing appearance remains unverified as fixed; the checkbox above stays open. New generation guidance has not been quality-benchmarked in a newly played campaign.
