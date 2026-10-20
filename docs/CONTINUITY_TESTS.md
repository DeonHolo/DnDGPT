# Campaign context tests

The first size experiment measured model-visible JSON, not model memory, whole-turn speed or long-campaign reliability. A compact view intentionally hides older log entries and world articles. The complete save stays available, but a model can still fail to retrieve it.

## Current decision

Use full saved state for story/history decisions unless the relevant facts are already available in context. Compact views remain available for routine actions with sufficient context. The default tool argument remains full. Successful saves and current rules can still be reused; this does not require a full read or extra verification call every turn.

The tests reproduced a separate write bug: copying the compact world's summary into an ordinary update replaced the world object and dropped omitted route/password details. Ordinary updates now merge world object fields recursively. Lists and scalar values still replace explicit values; they require complete relevant source data. An approved correction can intentionally replace the world object. Historical snapshots remain separate from current canon.

## Repeatable storage and transport tests

`tests/test_continuity_context.py` builds invented campaigns and checks:

- Early promises, current world rules and eight saved commitments survive 10, 100 and 300 successive saves, database reopening and historical reads.
- Current ability limits and quest objectives stay in turn views. The resume brief is deliberately smaller and cannot substitute for mechanics or full history.
- Reads do not change versions, audit events, pause or fictional time. A full read recovers omitted facts.
- Partial continuity updates preserve other notes. Editing a compact world summary preserves omitted keys, including nested world facts.
- Approved corrections retain their preview/approval requirement and can deliberately replace world information.
- The authenticated MCP response keeps the complete widget snapshot in metadata, outside the model-visible compact result. Counting that hidden snapshot as model memory would invalidate the comparison.
- Full remains the default read; empty continuity is labeled missing rather than invented.

Run from `dndgpt-app`:

```text
python -m pytest tests/test_continuity_context.py tests/test_continuity_recovery.py tests/test_chat_game.py tests/test_sources.py tests/test_rule_sections.py -q
python -m scripts.audit_continuity_context --saves 100
```

The audit writes a fact-visibility report and reproducible full/turn prompts under ignored `test-results/`. It makes no model calls or accesses to player campaigns. The availability counts are diagnostic, not a model score.

## ChatGPT smoke comparison — 2026-10-21

Two fresh temporary chats in the in-app browser received an invented save after 20 successive updates. Both showed the same Medium mode; no exact underlying model identifier was exposed. The prompt asked eight factual questions and one question deliberately absent from every save, with explicit instructions to request missing information rather than guess.

| Input | Observed behavior |
| --- | --- |
| Full save | Answered all eight recorded facts correctly and did not invent the absent fact. It unnecessarily requested a full save again for the absent fact, following the test's generic missing-information instruction. |
| Turn view | Answered all five visible facts correctly; requested full information for the three omitted facts; did not invent the absent fact. Its phrase “not recorded” was imprecise because the facts were recorded but omitted from that view. |
| Turn chat after manually supplying full save | Recovered all three missing answers, preferred the current password over an obsolete historical password, and correctly left the absent fact unknown. |

The full input was automatically displayed as a pasted document; the shorter input stayed inline. These were one run per view with a fixed fixture, not a randomized performance study. Full information was supplied manually, so this does **not** establish automatic MCP retrieval, long multi-turn RPG consistency or a model-latency improvement. Local response transcripts, input prompts, observations and screenshots are under ignored `dndgpt-app/test-results/continuity-*`.

## Published verification — application 1.0.32

Implementation commit `e0da11d4f409d798d10f812d7b6e242fb5c89087` passed 476 automated CI checks and packaging. Local affected suites passed 89 checks, 20 hosted-store contract checks and two final nested-world/transport checks. The live health endpoint returned 1.0.32. Production deployment `6ad7ef8525bd8c5b084d` and private probe deployment `6ad7ef83c70a3ff5a039` were ready from that commit.

Private hosted execution `6ad7f0c17c541bf5bbc5` passed all 14 existing hosting checks and 11 recovery/context checks, including omitted world-key preservation and full-history recovery. It used probe-owned disposable records, accessed no player campaign and made no model calls. The full run took 19.63 seconds; this is not one gameplay turn. One full-state read took 0.3432 seconds and one batched save took 1.1855 seconds. These isolated storage timings cannot predict ChatGPT response time.

An earlier synchronous probe hit Appwrite's 30-second synchronous limit. An asynchronous retry completed HTTP 200 but did not retain its response body; a subsequent synchronous run supplied the complete passing report. Record both the failure and successful verification rather than treating the timeout as a continuity failure or discarding it.

The connected app returned hardener hash `253b32c9bd127a88f52350b084c205903c6a1ceeddf857609d30fd3accd04820` (7,930 characters, one page) and rulebook hash `de22eff2140f683cda190f2227885b0be1c5cf9960fd0c5db8e7f0d5c478d3e8`. The rulebook response was a partial first page with a full-source hash, not a claim that the complete manual was read. Browser access was disabled in Work settings during final verification, so the cached ChatGPT tool catalog was not refreshed. Current hosted rules contain the safer guidance; tool parameters still default to full reads.

## Next model evaluation

Before broadly preferring compact views again, run repeated matched full/compact trials through the actual native MCP app with disposable campaigns. Vary early promises, amended facts, long absences, location history, sixth/eighth commitments, ability conditions, player intent and facts never recorded. Include ordinary actions that require no historical retrieval.

Record whether the model retrieves the missing source before adjudicating, follows current canon over obsolete logs, preserves unknowns and player agency, and avoids extra reads for already-known routine facts. Record real tool count and end-to-end turn time separately from input size. Require zero unauthorized mutations or fabricated critical facts; report each failure and the tested sample size. A small scripted comparison cannot establish reliability over arbitrary long campaigns.
