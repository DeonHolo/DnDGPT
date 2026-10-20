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

The earlier 91.6% figure measures model-visible JSON size in one mature-history fixture (65,087 to 5,488 bytes). It is not a tool or whole-turn latency percentage, nor proof of preserved story recall. Turn mode retains current mechanics/continuity but omits older logs and detailed world articles. Missing historical dependencies require a full read; facts never recorded cannot be recovered from a save. Long-campaign recall testing remains necessary.
