# Continuity and recovery release

Approved 2026-10-21. Baseline: `6dec766` on `main`.

## Scope and acceptance

- [x] Add concise causal transitions between resolved turns. Preserve player-authored thoughts, pending decisions, actual timing, and the existing two-decision obstacle ceiling.
- [x] Merge the approved campaign-themed Intelligent Story UI contract into the canonical presentation rules; keep the hardener short and synchronize bundled references.
- [x] Supply a bounded resume brief from committed state, including scene, player intent, unresolved threads and NPC commitments. Reading it cannot start/resume a game or mutate saved state.
- [x] Evaluate actual generated powers/classes separately from synthetic validation fixtures. Record evidence and remaining human judgments; test Utility across ordinary situations.
- [x] Add readable, owned save history and correction previews with existing explicit approval/version gates.
- [x] Add portable export and safe restore as a separate paused campaign. Reject malformed/oversized data, preserve source saves and ownership, and verify hosted Appwrite recovery separately from SQLite.
- [x] Add repeatable browser checks for Original, Reclaimed Codex, The Orrery and Ember Ledger at narrow/wide widths, including approvals, story spacing and all three ability tabs.
- [x] Document/measure normal-turn tool overhead. Reuse available current-version state and cached rules, batch legitimate rolls and one authorized save, and avoid routine history scans or redundant verification reads. Do not promise a model response time that has not been measured.
- [x] Run relevant regression checks, publish the tested revision, verify hosted state/resources, and report local, browser and live evidence separately.

## Boundaries

- Existing player campaigns are read-only during development and verification.
- Use disposable fixtures for writes, rolls, imports and recovery exercises.
- Keep character confirmation, adventure start, corrections and resume approvals distinct.
- Narrated, proposed and committed outcomes remain distinct. Presentation cannot change mechanics or reveal GM secrets.
- No plugin ZIP update is required for the active native MCP connection; hosted changes ship through the established Git/Appwrite deployment.

## Current work

Application 1.0.30 is published from `64ac23ed3153b03797815299afb28435cea8ffb2`. Production and private probe deployments match that commit. ChatGPT tool refresh completed, and the app details show the new history/import/export tools and compact-view instructions. No ZIP was uploaded. See docs/RELEASE_VERIFICATION_2026_10_21.md.

## Evidence

- Baseline working tree clean.
- Existing hardener already requires section/hash reuse and batched authorized updates.
- Existing SQLite backup tests are not evidence of hosted Appwrite restoration.
- Full local suite: 462 passed (collected before four later validation cases); final affected suites: 65 passed, including those cases.
- Browser matrix: 11/11 passed across four layouts at 390/1180px. Existing approval recovery: 6/6 passed across four layouts at 375/700/1100px. Simulated host, real local transport, disposable data; not ChatGPT.
- Actual read-only sample: 15 saved abilities, 12 Utility scenario judgments, one empty draft excluded. No live generation or gameplay mutation; findings in docs/GENERATION_REVIEW.md.
- Portable release builds with all JS/CSS assets; bundled rules match canonical sources. Nothing uploaded to the user's native app as a ZIP.
- In-app browser did not report a download event. Added copyable/selectable JSON fallback containing the exact export data; native host download behavior remains separate from file-content/restore validation.
- Final GitHub CI: 466 passed; both check/package and Pages deployment succeeded.
- Hosted Appwrite: 14 existing checks plus 9 new recovery/continuity checks passed in private execution `6ad7d8a860bc779f6bd4`; probe-owned fixtures only, zero model calls.
- Combined state/approval read: 0.4244 seconds and 6 storage API calls, compared with 0.8355 seconds and 11 calls for separate reads. Batched save: 1.1816 seconds. One hosted fixture run; no model latency claim.
- Model-visible campaign JSON: full 65,087 bytes, turn 5,488 bytes, resume 852 bytes. Full widget snapshot remains in hidden metadata; this is not a network-byte reduction claim.
- Live hardener hash `dba32db6dfe233e4c7481be03c21a36d041fafa6cdff022e85a47f53e6ff9817` and rulebook hash `77d7bd5b2a59f1f81c2a97384c691d77c1e2620c1f497b30397799d4582223a0` match canonical source. Hardener is one 7,923-character page. Rulebook verification fetched a partial page and verified the full-source hash, not a claim of reading all 405,051 characters.
- Copy campaign JSON was clicked in the in-app browser and returned the copied confirmation. File contents and restore were checked through the simulated host; no native download event was reported.

## Outstanding limits

ChatGPT model/render time and the host's tool selection are outside backend timing measurements. Actual generation quality must remain distinguished from schema/fixture tests.

## Enemy behavior follow-up — 2026-10-21

Chapter 14 now has an indexed `enemy-tactics` contract: a mechanical novelty gate for significant new enemy types/groups, varied answerable pressures, terrain use, knowledge-based controller targeting, morale and brief character dialogue. Existing stat blocks, player agency, actual summon rules and all approval gates remain binding. Profiles are prepared once and reused without extra per-round tools or audits. The compact hardener routes to this section and still fits one page.

Validation: 20 source-integrity, section-pagination and authenticated read-only MCP checks passed. These verify preservation and delivery, not whether a ChatGPT campaign consistently follows the new prose. Publication verification is recorded separately below.

Published application 1.0.31 from `3a261e52a8a00539d6624147d8799f745b3b6e76` through Appwrite deployment `6ad7e76e0985c4a09ce8` (ready, automatic activation enabled). GitHub CI passed 467 tests and packaging; Pages succeeded. The connected native app returned the full 3,909-character `enemy-tactics` section with source hash `15ac277c963e021a598e650f18803cc85679a8b884985e46c8283567dc9cdda4`; its 7,991-character hardener is one page with hash `2a60337b20d08bbddf4a4c5fcacf9a96b60062d55ac31d85d099b2f404c25456`. Verification read rules only; no player campaign was advanced or changed.

The earlier 91.6% figure measures model-visible JSON size in one mature-history fixture (65,087 to 5,488 bytes). It is not a tool or whole-turn latency percentage, nor proof of preserved story recall. Turn mode retains current mechanics/continuity but omits older logs and detailed world articles. Missing historical dependencies require a full read; facts never recorded cannot be recovered from a save. Long-campaign recall testing remains necessary.

## Campaign context tests and write safety — 2026-10-21

Added a repeatable synthetic fact-availability audit and nine continuity cases, covering 10/100/300 consecutive saves, reopening, historical snapshots, read-only views, retained commitments, current mechanics, partial world edits and the authenticated MCP boundary. Before the fix, the new suite reproduced world detail loss (7 passed, 1 failed). Ordinary world updates now merge object fields recursively; approved corrections can still replace the object. Lists/scalars retain explicit replacement semantics. No existing player campaign was changed.

Changed rule/tool guidance to use full state for story/history decisions unless relevant facts are already in context. Compact views remain optional for sufficient-context turns; full remains the default argument. The revision is reversible, the hardener remains one page and bundled references are synchronized. Normal batching and successful-save verification still apply.

Local verification: 89 relevant continuity/chat/rule checks passed, then 20 hosted-store contract checks passed. Final edits to the nested-world and MCP transport cases were checked separately. The independent 300-save audit retained all eight source facts in full, five in turn and two in resume views; those are availability counts, not model recall scores.

In-app ChatGPT smoke comparison: full input answered 8/8 recorded facts; compact input answered its five visible facts and requested full information for three omissions; manually supplying full recovered 3/3. Both avoided inventing the deliberately absent fact. One run per view with explicit instructions and no native MCP retrieval trial; no latency or long-game reliability claim. See docs/CONTINUITY_TESTS.md. Hosted publication evidence follows after deployment verification.

Published 1.0.32 from `e0da11d4f409d798d10f812d7b6e242fb5c89087`; CI passed 476 checks and packaging. Production health and connected rules match the implementation. Hosted private execution `6ad7f0c17c541bf5bbc5` passed 14 hosting plus 11 context/recovery checks in 19.63 seconds, with no player-campaign access or model calls. Earlier synchronous timeout and the response-less asynchronous retry are recorded in docs/CONTINUITY_TESTS.md. Final two transport/nested-world cases passed. Browser access was disabled during final tool-catalog refresh; current hosted rules carry the safer guidance and full remains the default.

Goal acceptance: long save retention, safe compact-world updates, controlled full/compact model comparison, published safeguards, hosted checks and documented evidence limits are complete. Repeated actual native-MCP retrieval/gameplay evaluation remains a distinct future study and has not been claimed as passed.

## Positive ability descriptions — 2026-10-21

Application 1.0.33 removes the conflicting requirement for visible skill caveats, limitations and counterplay blocks. The rulebook, compact hardener, presentation contract and bundled GM instructions now require positive effects and actual upgrade changes. The GM retains complete mechanics and adjudicates unintended uses when proposed, before spending a known illegal action's cost.

The shared ability inspector hides existing named disclaimer fields/sections, unchanged upgrade prose, default future-cast assurances and duplicate unchanged damage/duration facts. Overview, Full rules and Upgrades remain functional across all four layouts. This is display-only cleanup; no player campaign or owned mechanical source was edited.

Validation: 44 source-integrity, pagination, layout, standard-rule and packaging checks passed. The final simulated-host browser run passed 23/23 checks, including the supplied HP-upgrade pattern at narrow/wide widths in every layout, structured prose, retained costs/triggers and unchanged input/persisted state. One intermediate browser run used the test server's previously cached HTML; restarting the fixture server loaded the final renderer and passed the stricter unchanged-stat check. The reversible rule audit is `positive-ability-descriptions-2026-10-21.json`; the hardener is 7,979 characters and bundled references match. Hosted publication is verified after the Git/Appwrite build.

Published from `eb647288e4036a2c91ef03fefc7dc2f8781f7a7f` in active, ready production deployment `6ad7fa2eea05f927b983`. GitHub CI passed all 476 checks and packaging; Pages succeeded. The connected native MCP returned the new one-page hardener hash `32ec509cdcdf633b6db03f5ac5e9011e9a2baaf6d1283eaa2b12ae443e245867` and full rulebook source hash `761098a20d98f823f0021534a0057401cbf7df8baf2ec941327f6e057441c884`, matching local sources. Authenticated Appwrite health execution `6ad7fc0cd6ebda11af12` returned 200 and version 1.0.33 using the configured service Host; the earlier generic HTTP client returned 403 and an execution without that Host returned 421. No runtime security settings or campaign records were changed. No ZIP was uploaded to the native plugin. Existing prose inside an unlabelled freeform sentence is not semantically rewritten by the renderer; future GM descriptions follow the new writing rule.
