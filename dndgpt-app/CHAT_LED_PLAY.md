# Chat-led first playable release

The user's 2026-10-16 steering supersedes the full-engine-first release sequence: prioritize quick regular-Chat play, tolerate occasional GM mistakes, and use the dashboard's saved data as memory. The complete rules engine is optional later work, not a condition for this first release. Preserve both complete edition1.0 rule files.

ChatGPT remains the Game Master using the user's Chat subscription. It reads authenticated saved data through MCP, adjudicates from the rulebook, and submits one batched saved update for a resolved turn. The dashboard renders that same record; ChatGPT does not continuously see or control the dashboard without a tool call. No inference API is needed.

Keep ownership, bounded JSON validation, version checks, atomic saves, retry deduplication, and recoverable change history. Validate data shape and basic resource bounds rather than requiring every power, item, summon or quest to have executable rules. A stale update must reread and reconcile; never silently overwrite another turn. Corrections are new recorded updates, not history deletion.

Create a fresh draft only on request. After final creation choices, save the completed build, Your story, class-budgeted equipment and opening together with begin_adventure=true. No character/start approval follows. Advancement selections and banking commit directly; once pending tracks are resolved, clear the freeze and continue queued actions automatically. An explicit manual pause stays paused. Existing development sandboxes retain their original behavior.

The immediate acceptance target is a fresh disposable record whose character, ability, item and story changes can be saved in a single turn, displayed without rebuilding the UI, retried without duplication, reopened, and corrected. Verify it in regular Chat before claiming playable integration. Stable hosting and a second user's installation remain separate delivery tasks; a temporary tunnel still depends on this computer.

Working candidate1.0.11 implements chat-led saves locally. The installed server/plugin versions and live acceptance are recorded in CLIENT_ACCEPTANCE.md; source implementation alone is not live verification. The existing engine creation/combat gates stay off.

## Saved data contract

`create_chat_game(name,action_id,disposable=false)` creates a fresh paused `character_draft`. `save_chat_update(campaign_id,action_id,expected_version,summary,changes)` atomically saves a bounded batch. `get_campaign` reads current state; `get_chat_version(campaign_id,version)` reads an owned historical version. HTTP mirrors are `/api/chat-games`, `/api/campaigns/{id}/chat-updates`, and `/api/campaigns/{id}/versions/{version}` behind the same authentication/scopes.

Changes accept partial `character` (nested attributes merge), equipment slot to inventory-ID/null, `name`, `current_location`, `opening_preview`, `notes`, `fictional_time_seconds`, `level_up_freeze`, `world`, `continuity`, and whole replacement `creation`/`advancement`/`funds` objects. Ordinary `world` saves recursively merge object fields, preserving omitted facts; lists and scalars still replace their values. `continuity` merges its named fields. Read complete relevant state before replacing lists, objects or collections; never reconstruct them from a compact excerpt. Reviewed corrections retain their existing world replacement semantics. `upsert` merges records by stable ID; `remove` lists IDs; `replace` explicitly replaces a collection. Collections are abilities, conditions, summons, enemies, inventory, supplies, quest_log, world_log and generation_ledger. Equipped inventory records remain in inventory but appear under the Equipment subtab. Unknown/server-controlled fields are rejected. Limits protect record size and resource ranges; the GM adjudicates game semantics.

Example batch: `{"character":{"hp":80},"upsert":{"world_log":[{"id":"gate-arrival","text":"Reached the copper gate."}]}}`.

`propose_action` supports manual `pause{}`, `resume{}` and `correct_chat_state{changes,reason}` in chat mode. These reviewed operations retain app approval. Creation completes directly through `save_chat_update(begin_adventure=true)` after the actual build choices, populated story, equipped outfit and opening are saved. Drafts cannot advance fictional time; ordinary updates cannot modify a manually paused adventure. Corrections append history and require review. Legacy mechanical commands cannot bypass these safeguards.

The response is a persisted receipt. Repeat the exact action ID and arguments on uncertain delivery, including after restart. A changed retry or stale version returns409. Read current state after conflicts; do not replay a reward. Historical/duplicate receipts can describe an older version, so consumers must not replace newer state with them. This protects persistence, not the creative quality or perfect correctness of every GM ruling.
