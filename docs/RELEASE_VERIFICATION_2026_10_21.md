# Continuity and recovery verification

Application **1.0.30**, verified October 21, 2026 (Asia/Singapore). Implementation: [64ac23e](https://github.com/DeonHolo/DnDGPT/commit/64ac23ed3153b03797815299afb28435cea8ffb2).

Production Appwrite deployment `6ad7d7ced281ae23f819` and private probe deployment `6ad7d7cd9fa1fa0dc371` both report that exact commit and `ready` status. The native ChatGPT connection was refreshed in the in-app browser; its details show the new history, export/import and compact-view tool descriptions. Its identity and OAuth connection were preserved. No plugin ZIP was uploaded.

## Local and browser evidence

- Full local suite: 462 passed. A final affected-area run passed 65 checks, including four validation cases added after the full run started.
- Final [GitHub check/package run](https://github.com/DeonHolo/DnDGPT/actions/runs/39497629197): **466 passed**. [Pages deployment](https://github.com/DeonHolo/DnDGPT/actions/runs/39497628131) succeeded.
- New browser page: **11/11 passed**, covering Original, Reclaimed Codex, The Orrery and Ember Ledger at 390/1180px, character confirmation, collapsed/padded story content, all three ability tabs, seven chapters, read-only history, exact correction approval and separate paused restoration.
- Existing approval-recovery browser page: **6/6 passed**, including expired review/reopen, separate confirmation/start and campaign switching across four layouts at 375/700/1100px.

Browser checks used Chromium in the in-app browser, a simulated MCP Apps host, real authenticated local transport and disposable SQLite data. They did not exercise ChatGPT's own generated Story UI. The in-app browser did not report a native download event. The exact JSON fallback and file restoration passed; clicking **Copy campaign JSON** returned its copied confirmation. Host download support remains separate from file-content integrity.

## Hosted Appwrite evidence

Private execution `6ad7d8a860bc779f6bd4` completed with HTTP 200 and `status=passed`. Fourteen existing checks covered creation, exact save/approval retries, historical versions, separate character/start gates, fresh-instance reopening, ownership, dashboard state/preferences, genuine disposable roll retry and event integrity. Nine additional checks covered:

- continuity in the existing batched save;
- read-only resume and paged history;
- compact views retaining current mechanics;
- corruption rejection;
- a separate paused portable restore, exact retry, intact source and fresh-instance reopening of the restored record.

The probe used newly generated fixture owners, reported `real_campaign_accessed=false` and `model_api_calls=false`, and retained private execution permissions (`execute=[]`, public triggering disabled). It did not access or advance player campaigns. This verifies portable snapshot restoration on the real Appwrite store, not provider-backup or disaster recovery.

## Measured overhead

One hosted run used a disposable mature-history fixture containing 60 log records. Timings include storage work, not ChatGPT generation or host scheduling:

| Operation | Seconds | Storage API calls |
| --- | ---: | ---: |
| Separate state and approval reads | 0.8355 | 11 |
| Combined state and approval read | 0.4244 | 6 |
| Batched save including continuity | 1.1816 | 11 |
| One history page | 0.4035 | 6 |
| Export current snapshot | 0.3445 | 5 |
| Restore paused copy | 1.1146 | 9 |

Serialized model-visible campaign JSON was **65,087 bytes** for full state, **5,488** for the turn view and **852** for the resume view. The widget still receives a complete snapshot in hidden metadata. These figures measure model-context payload, not total network traffic, tokens or a guaranteed turn duration. No history, recovery, evaluation or separate continuity call is required in a normal turn.

## Rules and generation review

Authenticated hosted rule reads returned the canonical hardener SHA-256 `dba32db6dfe233e4c7481be03c21a36d041fafa6cdff022e85a47f53e6ff9817` and rulebook SHA-256 `77d7bd5b2a59f1f81c2a97384c691d77c1e2620c1f497b30397799d4582223a0`. The hardener fits in one 7,923-character page. The rulebook read verified its complete-source hash from a partial page; it was not a full-manual reading claim. Integrity checks reverse the recorded edits to verify unrelated source preservation, and bundled references match.

[Generation review](GENERATION_REVIEW.md) covers 15 actual saved abilities and 12 Utility scenario judgments. It records narrow use cases and incomplete mechanics rather than counting every sample as a pass. It remains a single qualitative review, not proof of balance, originality, observed usefulness or long-campaign reliability.
