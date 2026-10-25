# Sovereign System implementation

Approved 24 October 2026. The original startup document is design material, not authorization to create or play a campaign. Its old separate character/start approvals and seven-chapter restriction are superseded by the user's current instructions.

## Release requirements

- [x] One connection and existing tools select the game's rules and dashboard.
- [x] Preserve the Age of Convergence rulebook except the separately requested shared tooltip-row fix, recorded in its reversible integrity audit. Compile Sovereign rules from that source, exact scoped replacements and new modules; fail on missing/ambiguous replacement anchors.
- [x] Save game identity at creation. Existing unlabelled saves remain Age of Convergence. Filter saved-game listings on the server; switching games changes no campaign.
- [x] Store domain milestones, commanders, formations, operations and battle fronts in the campaign, with independent progression and once-only rewards.
- [x] Keep personal powers, sovereign powers and entity-owned abilities distinct, with parent-owned upgrades and all three ability tabs.
- [x] Resolve recorded formation phases inside the normal atomic save, using genuine rolls and retry protection. Advance operations only through fictional time.
- [x] Add a Sovereignty chapter and game selector to the existing responsive dashboard. Preserve Gallery, history, corrections, imports, layouts and atmosphere choices.
- [x] Verify preservation, routing/isolation, progression, battle arithmetic, retry safety and narrow/wide real browser controls before publishing.

## Play contract

Keep approximately 75% personal adventure and 25% strategy. A new sovereign begins with a functioning class-specific domain, major autonomous commander and useful forces. Classes have genuinely different production, command, expansion and recovery rules. The class board contains eight Unique sovereigns; ordinary subsequent acquisition retains the shared rarity rules. Charm governs class-specific sovereign mechanics. Starting Luck allocation remains a player choice.

Character XP, domain milestones, formation veterancy and commander XP are separate tracks. Creation grants one free permanent Sovereign Evolution after Class selection, within an existing creation board. Each gained character level then guarantees one permanent significant Sovereign Evolution for the actual domain, general or army. The player chooses from five compatible offers; applying the selection needs no further approval. Routine entity growth is automatic. Domain development still follows its finite published milestone; it does not replace the guaranteed character-level improvement.

The game selector changes the saved-game list and available chapter. It never converts a save, creates a campaign, rolls or advances time. A campaign ID determines its authoritative rules; a contradictory game argument is rejected. Layout and reading atmosphere remain independent presentation preferences.

## Evidence

The new browser matrix passed 7/7 checks across Original, Reclaimed Codex, The Orrery and Ember Ledger at 390/1100px, including real game/saved-campaign selection, independent commander displays, three-tab powers, personal/sovereign filters, domain choices, late responses and unchanged gameplay. This uses authenticated local transport and disposable campaigns, not a native ChatGPT acceptance run. Subsequent shared regression and publication evidence is recorded below when complete.

Release candidate `8706667`: [full GitHub checks](https://github.com/DeonHolo/DnDGPT/actions/runs/40101660496) passed 565 tests, the isolated hosted-dependency import and portable packaging. Local focused source/rules/game checks passed 43; targeted import/credit/ledger checks passed four. The final browser run passed the seven new Sovereign checks, 24 existing player-view checks and eight quest/Gallery checks, including selection context with no unsolicited chat message. A first candidate had 560 passing checks and one failure caused by an extra REST response field; retaining the original REST list response fixed compatibility. No failing candidate was deployed to production.

The base-phase resolver and progression are executable; arbitrary novel ability prose remains GM-adjudicated. Neither schema tests nor browser fixtures certify generated class quality, model prose, native phone behavior, campaign balance or a model latency percentage.

## Using the two games

Open the existing DnDGPT dashboard and choose **Game**. **Saved game** then contains only that game's campaigns. Switching changes no save, character, time or dice. **New campaign** sends the explicit new-game request to chat. Choosing a different game does not migrate an existing campaign. Each account still owns its campaigns in both games; filtering is a navigation boundary, with the existing account ownership checks protecting every read/write.

The existing `read_rules`, `create_chat_game`, `list_campaigns`, `get_campaign`, `save_chat_update` and `render_dashboard` tools handle both games. For a saved campaign, `read_rules(campaign_id=...)` derives the book from its saved identity. Before creation pass `game_id=sovereign-system` or `age-of-convergence`. Contradictory game/campaign arguments are rejected. Rules and the checklist are composed from shared source; the runtime does not ask a model to rewrite the manual. Both checklists fit one page, including compact response metadata. Cache by game and source hash; keep the game/campaign on subsequent pages.

The selected game/campaign is published to host model context without posting a chat message. This uses [the supported model-context mechanism](https://developers.openai.com/plugins/build/chatgpt-ui#keep-temporary-ui-state-in-the-ui) and widget-state compatibility. It is selection context, not a request to continue play. Ordinary progress and battle phases use the usual save; no separate sovereign read or battle tool is mandatory each turn. Actual thinking/narration time remains model-dependent.

## Progression and saves

Character growth follows the shared XP rules. Each gained level guarantees one permanent significant Sovereign Evolution on Domain, General or Army. An internal once-only ledger tracks the award separately from ordinary SP and quest evolutions; it is not presented as another player currency. General XP carries across thresholds of 100 + 50*(current level-1). Formation veterancy uses cumulative thresholds 0/100/250/450/700/1000. Domain advancement requires its finite, published milestone and one of three development choices. Force capacity is declared from the actual class and checked against the saved roster.

Standing orders have fictional start/due times, objectives and mandates. A due report requires actual adjudication and a recorded outcome; passing real time alone does nothing. Current snapshots keep the latest 50 full battle reports plus compact permanent retry receipts. Earlier full reports remain in save-history versions. Export/import retains game identity and sovereign state and restores a separate paused copy.

## Edited Intelligent UI prompt

[Copyable prompt](INTELLIGENT_STORY_UI_PROMPT.txt): 4,839 characters including its final newline. The added fix gives tooltip category, title, description and stats explicit separate rows, gaps, typography and wrapping while preserving the inline story trigger and full opaque four-sided border. The shared rulebook and both game checklists inherit the same instruction. Prompt delivery cannot prove that a future native generated tooltip renders correctly.

## Permanent Sovereign progression — 25 October 2026

Sovereignty owns the three passive foundation histories: Domain, General and Army. Each has Overview, Full rules and Upgrades beside the actual domain, commander or formation records. Regular Skills contains attacks, reactions, utility and temporary commands, including powers that affect allies or armies. The old personal/sovereign skill filter is removed.

Creation previews the actual functioning domain, persistent major general and useful army alongside a solo-viable regular kit. It records three UNIQUE passive foundation parents with sovereign_role=domain/general/army; these establish current functions, not extra casts. Fully expand the selected class during the next existing creation response. The same four choice stages remain.

A chosen Sovereign Evolution changes the combined foundation and at least one real owned capability in the same atomic save. The acquired child references target_id/capability_id through sovereign_changes; its referenced domain capability or general/formation ability records source_evolution_id, activation=Passive and duration=Permanent. Temporary buffs, ordinary active skills, nonexistent targets, unchanged records, duplicate spending and replacement of a passive foundation with an active command are rejected. Novel mechanical significance remains a GM/design judgment; a schema cannot certify balance or interpret arbitrary prose.

Existing adventures retain their history and earned commands. The interface continues to show older active commands in regular Skills. A missing or misclassified older foundation needs a requested correction using the actual saved class; this release does not silently invent replacement powers in player campaigns.

The compact territory view includes known fronts, returning expedition reports and recent completed developments. It omits unrevealed enemy operations. Legacy temporary commands remain visible and count as regular skills even if their older stored scope label was sovereign; they do not invalidate three otherwise complete permanent foundations or become eligible for a guaranteed foundation upgrade.

## Creation completion compatibility — 1.0.44

The final player choices start play through save_chat_update with changes.begin_adventure=true, using the existing changes object supported by older tool catalogs. The top-level flag remains supported. Retired confirmation/start proposals return a read-only handoff to that save, with no approval proposal. Actual missing build, story or outfit prerequisites still reject atomically.

The starting gift is separate from the Level 2 award. Older saves receive the missing allowance once on their next ordinary committed save. Previously selected and permanently applied creation overrides are accounted as already spent; their powers are preserved and are not granted again. Stable receipt and skill IDs remain internal; prose, offers, upgrade descriptions and display fields use actual names.
