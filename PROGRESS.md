# Continuity and recovery release

Approved 2026-10-21. Baseline: `6dec766` on `main`.

## Scope and acceptance

- [x] Add concise causal transitions between resolved turns. Preserve player-authored thoughts, pending decisions, actual timing, and the existing two-decision obstacle ceiling.
- [x] Merge the approved campaign-themed Intelligent Story UI contract into the canonical presentation rules; keep the hardener short and synchronize bundled references.
- [x] Supply a bounded resume brief from committed state, including scene, player intent, unresolved threads and NPC commitments. Reading it cannot start/resume a game or mutate saved state.
- [x] Evaluate actual generated powers/classes separately from synthetic validation fixtures. Record evidence and remaining human judgments; test Utility across ordinary situations.
- [x] Add readable, owned save history and correction previews with existing explicit approval/version gates.
- [ ] Add portable export and safe restore as a separate paused campaign. Reject malformed/oversized data, preserve source saves and ownership, and verify hosted Appwrite recovery separately from SQLite.
- [x] Add repeatable browser checks for Original, Reclaimed Codex, The Orrery and Ember Ledger at narrow/wide widths, including approvals, story spacing and all three ability tabs.
- [ ] Document/measure normal-turn tool overhead. Reuse available current-version state and cached rules, batch legitimate rolls and one authorized save, and avoid routine history scans or redundant verification reads. Do not promise a model response time that has not been measured.
- [ ] Run relevant regression checks, publish the tested revision, verify hosted state/resources, and report local, browser and live evidence separately.

## Boundaries

- Existing player campaigns are read-only during development and verification.
- Use disposable fixtures for writes, rolls, imports and recovery exercises.
- Keep character confirmation, adventure start, corrections and resume approvals distinct.
- Narrated, proposed and committed outcomes remain distinct. Presentation cannot change mechanics or reveal GM secrets.
- No plugin ZIP update is required for the active native MCP connection; hosted changes ship through the established Git/Appwrite deployment.

## Current work

Application 1.0.30 implemented. Local checks passed; publishing and private hosted recovery/timing verification remain. The active native MCP connection needs hosted deployment and tool refresh, not a ZIP upload.

## Evidence

- Baseline working tree clean.
- Existing hardener already requires section/hash reuse and batched authorized updates.
- Existing SQLite backup tests are not evidence of hosted Appwrite restoration.
- Full local suite: 462 passed (collected before four later validation cases); final affected suites: 65 passed, including those cases.
- Browser matrix: 11/11 passed across four layouts at 390/1180px. Existing approval recovery: 6/6 passed across four layouts at 375/700/1100px. Simulated host, real local transport, disposable data; not ChatGPT.
- Actual read-only sample: 15 saved abilities, 12 Utility scenario judgments, one empty draft excluded. No live generation or gameplay mutation; findings in docs/GENERATION_REVIEW.md.
- Portable release builds with all JS/CSS assets; bundled rules match canonical sources. Nothing uploaded to the user's native app as a ZIP.
- In-app browser did not report a download event. Added copyable/selectable JSON fallback containing the exact export data; native host download behavior remains separate from file-content/restore validation.

## Outstanding limits

ChatGPT model/render time and the host's tool selection are outside backend timing measurements. Actual generation quality must remain distinguished from schema/fixture tests.
