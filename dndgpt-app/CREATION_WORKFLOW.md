# Saved creation drafts — development contract

The creation repository persists the existing rule-derived phase contracts; it is
not a playable character generator. Bounded fixture programs now execute, but are
not evidence of semantic originality/tier strength. Supported starting loadouts,
derived previews and the confirmation gate are implemented; full item mechanics,
semantic build certification and the player approval/creation screen remain unfinished.

Every displayed offer now requires supported programs, including all five Background riders bound to actual owned parents. The final build gates recheck unselected legacy options too. Read-only `board_programs` diagnostics preserve old saved bytes; semantic/tier certification remains false. See OFFER_VALIDATION.md for the separate program and semantic gates and old pending-approval behavior.

## Registration and identity

`create_app(..., enable_creation_drafts=True)` registers the development adapters
for an isolated test application. The default is `False`; the existing live
`app.server:app` does not expose these routes/tools. There is deliberately no
production environment switch in this slice. All requests still require verified
OAuth tokens. Ownership comes from issuer + subject through `owner_id`, never a
request argument or shared OAuth client ID. No model-inference dependency is added.

Authenticated read tools: `list_creation_drafts`, `get_creation_draft`,
`audit_creation_draft`. Write-scope proposal tools: `propose_creation_start`,
`propose_creation_transition`. `confirm_creation_transition` has app-only
visibility and requires a widget-only approval token. Host app visibility is a
client contract, not an independent user-presence attestation from the backend.
The actual creation approval UI/live host flow has not yet been exercised.

REST development adapters expose `/api/creation-drafts` (list/start proposal),
`/api/creation-drafts/{id}` (read), and its `/proposals` and `/events` children.
There is no creation HTTP confirmation route. HTTP responses are ordinary
authenticated JSON; the MCP adapter separates `_meta` from model-visible content.

## Stored state and decisions

| Phase | Legal transitions |
|---|---|
| `luck` | `allocate_luck` with points or an explicit default |
| `class` | Privately review 12–15 seeds and real available history inside the five-Class roll proposal; complete the five offers, then `choose_class` |
| `signatures_titles` | Roll/complete five Signatures and five Titles, then `choose_sources` |
| `background_attributes` | Roll/complete five owned-parent Backgrounds, then `choose_background` and remaining attributes |
| `character_confirmation` | `prepare_starting_build` with a supported loadout, then `confirm_character` with `confirmed=true` |
| `opening_preparation` | `prepare_opening` with public preview and six private commitment groups |
| `adventure_authorization` | `authorize_adventure` with `authorized=true` |
| `adventure_authorized` | Terminal draft contract; no campaign materialization in this slice |

Class rolling requires the private review packet documented in CLASS_PREPARATION.md. Read preparation for actual same-owner draft history; never invent past builds. The existing roll proposal contains the evidence, so this adds no player microdecision or extra creation turn. Approval rechecks current history before RNG and saves the exact reviewed context; only five shortlisted seeds roll. Complete semantic/tier review remains unfinished.

Every start and transition is an inert proposal until app approval. Proposing a
roll validates all five concepts/dependencies but consumes no RNG. Approval
rechecks the current version, draws once and atomically saves the state, immutable
receipts, event and committed response. A retry of the same proposal/token returns
that stored response; it never applies a selection twice or rolls again. A reused
action ID with different arguments fails. Competing versions fail explicitly.
Committed retries return the original receipt/snapshot even after later choices;
a client must not replace a newer displayed version with that older snapshot.

Pending approval tokens expire after 15 minutes. Already committed retries remain
recoverable after that interval. Pending tokens are recoverable through account-
owned widget metadata after a server/process restart. A changed draft can make an
older approval stale; re-inspect instead of silently substituting a new decision.

`creation_drafts_v1`, `creation_proposals_v1` and `creation_events_v1` are separate
from campaign tables. Schema initialization adds tables without importing or
rewriting campaign records. An approved draft never resumes an existing campaign
or advances fictional time. Each committed version has a state digest and chained
event receipt; inconsistent edits are detected, but an administrator able to
rewrite the entire database is outside that integrity guarantee.

## Visibility

- Normal draft reads display only complete offer boards. Unfinished kits remain
  unpublished. The optional preparation view supplies fixed final tiers and actual
  owned powers so the GM can prepare kits without rerolling them.
- Raw rarity/Luck receipts appear only in `audit_creation_draft(show_rolls=True)`;
  ordinary reads/preparation/audits redact them. A caller must use that option only
  for an explicit player audit request.
- Private opening commitments are stored and hashed but excluded from public
  previews, approval previews, preparation views and audits, including raw-roll
  audits. A later campaign materialization step must transfer them privately.
- Free-text descriptions are data. They are never evaluated as code or used as
  unrestricted state patches.

Read STARTING_BUILDS.md for the required loadout, selected executable powers,
derived resource/DC preview and exact confirmation freeze. Build preparation does
not replace chosen powers, reroll source rarities or grant unspecified gear bonuses.

## Verification and remaining work

`tests/test_creation_repository.py` covers durable phase transitions, owner
boundaries, no RNG before approval, duplicate/concurrent retries, stale versions,
expiry, rollback, private-field redaction, separate-process recovery and online
backup restore. `tests/test_creation_transport.py` covers signed-token HTTP/MCP
identity, scopes, hidden approval metadata and default-disabled registration.

These are local tests with disposable data, not real-provider or live-Chat
creation acceptance. The eight full-goal workstreams remain open in LAUNCH_PLAN.md.
Bounded item powers now execute through the shared runtime; see ITEM_RUNTIME.md.
Next: complete all-five semantic/tier certification and remaining item contexts, then a real
creation/approval UI, authorized campaign materialization and a disposable
regular-Chat rehearsal. Supported loadouts and selected source-program validation
already gate confirmation; see STARTING_BUILDS.md.
