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

## Next model evaluation

Before broadly preferring compact views again, run repeated matched full/compact trials through the actual native MCP app with disposable campaigns. Vary early promises, amended facts, long absences, location history, sixth/eighth commitments, ability conditions, player intent and facts never recorded. Include ordinary actions that require no historical retrieval.

Record whether the model retrieves the missing source before adjudicating, follows current canon over obsolete logs, preserves unknowns and player agency, and avoids extra reads for already-known routine facts. Record real tool count and end-to-end turn time separately from input size. Require zero unauthorized mutations or fabricated critical facts; report each failure and the tested sample size. A small scripted comparison cannot establish reliability over arbitrary long campaigns.
