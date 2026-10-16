# Private pre-roll Class preparation — development contract

The complete edition 1.0 rulebook, lines 633–657, requires roughly 12–15 private Class seeds, five distinct finalists including a genuine summoner, mechanical comparison and checks against actually available history. Only the five finalists receive independent rarity/Luck rolls. `app/class_preparation.py` now records and validates that preparation as data; regular ChatGPT still supplies the creative reasoning. There is no class catalogue, inferred past campaign, additional player questionnaire or model-inference API.

## Authoring sequence

Use the existing default-off `enable_creation_drafts=True` development adapter and the existing approved Luck transition. Read `get_creation_draft(include_preparation=true)` before drafting the Classes. `preparation.known_classes` contains only complete Class offer boards from this account's other saved creation drafts. Each row has its actual `draft_id`, typed `concept` and opaque `reference`. Empty history means none is available in that scope. No campaign records or other account's drafts are read or imported.

Submit the existing `roll_board` transition with `kind="classes"`, the five `concepts` in shortlist order, and one private `review` object:

- `seeds`: 12–15 distinct Concept records, using the existing ID/name/seven-component fingerprint/summoner fields. Class seeds cannot have a Background parent.
- `shortlist`: exactly five seed IDs in the order to be rolled. Their complete records must match `concepts`, including their mechanical fingerprints.
- `decisions`: one `{seed_id, selected, reason}` for every private seed, including every rejected alternative. Nonblank reasons and selection membership are checked.
- `differences`: all ten unordered finalist pairs, each once. Each entry has `left`, `right`, `permission`, `economy`, `tactical_decision` and `independent_utility`.
- `history_differences`: one comparison for each finalist against every actual available history reference. `left` is the finalist ID and `right` is the server-issued history reference; the other four evidence fields are the same as above. Use an empty array only when that actual history is empty. The request cannot supply or replace the history itself.

Both proposal and approval validate the packet against server-owned history before any random draw. A newly completed Class board in another owned draft can invalidate a pending proposal's history review: re-read, extend the evidence and submit a new proposal/action ID. This consumes no rarity draws or draft version. A committed retry always returns its original stored result without rechecking future history or rerolling.

Approval saves the packet, the exact history context checked, the five rarity receipts, the next draft version and the event atomically. No separate preparation transition or extra player choice is added. The existing four-turn presentation and separate character/adventure authorizations remain. The committed context is retained for final build/opening/adventure validation; later unrelated drafts do not retroactively rewrite its review.

## Privacy and compatibility

Normal reads, lists, proposals, committed responses and audits omit the private seeds/reasons/comparisons. Audits contain only the review/context digests, seed count and the existing five-candidate receipts. The explicit GM preparation read recovers private authoring evidence and actual history; never copy that internal pool into the player's options or HUD. Hidden app-approval tokens remain in MCP `_meta`, outside `structuredContent`.

New review/context fields are optional for decoding old saved schemas. Integrity checks hash the stored JSON before decoding adds defaults; inspection never edits those bytes or historical receipts. A pre-review rolled draft remains readable but cannot be finalized by silently fabricating evidence after its rarity was known. Old pending five-only Class roll approvals are revalidated and fail with `invalid_creation` before draws or writes. There is no retroactive backfill command.

The development guard allows at most 2,000 actual history rows and 10,000 history comparisons, in addition to the existing 1 MB request bound. These are technical limits, not gameplay laws; exceeding them fails rather than silently truncating available history.

## What this establishes

Structural checks establish a recorded pool size, exact shortlist, coverage of selected/rejected seeds, pair/history comparison coverage, account isolation and pre-roll ordering. Exact normalized reuse of any actual prior mechanical fingerprint is rejected even when its theme changes. Existing all-five program, rarity, provenance, native Free Action, actual summoning and owned-parent Imprint checks remain mandatory.

Arbitrary prose is not proof of creative originality, meaningful mechanical separation, solo viability or rarity strength. `semantic_tier_certification` remains false. Full semantic/tier/full-kit review, remaining executable mechanics, the actual player creation/approval UI, authorized campaign materialization and a disposable regular-Chat rehearsal remain required. Both development adapters default off and full-game capability flags remain false.

Evidence uses disposable fixtures: `tests/test_class_preparation.py` covers private review/history, rejected malformed packets, fixed draw counts, later-history conflicts, legacy compatibility and fresh-process online-backup recovery. `tests/test_class_preparation_transport.py` exercises the signed HTTP/MCP gate, hidden approval metadata, scopes and ownership. The focused suite passed 23 cases (`test-results/class-review-focused.xml`); the full final-source regression passed 299 cases with two existing dependency warnings (`class-review-full-suite.xml`). These checks are separate from live Chat, real-provider, hosting and two-account acceptance.
