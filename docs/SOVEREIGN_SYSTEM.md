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
- [ ] Verify preservation, routing/isolation, progression, battle arithmetic, retry safety and narrow/wide real browser controls before publishing.

## Play contract

Keep approximately 75% personal adventure and 25% strategy. A new sovereign begins with a functioning class-specific domain, major autonomous commander and useful forces. Classes have genuinely different production, command, expansion and recovery rules. The class board contains eight Unique sovereigns; ordinary subsequent acquisition retains the shared rarity rules. Charm governs class-specific sovereign mechanics. Starting Luck allocation remains a player choice.

Character XP, domain milestones, formation veterancy and commander XP are separate tracks. A character level also earns one sovereign evolution credit. Routine entity growth is automatic; the player chooses significant domain development and their own sovereign evolutions. Published milestones have finite objectives and a fixed next level. Development never requires another confirmation after choosing it.

The game selector changes the saved-game list and available chapter. It never converts a save, creates a campaign, rolls or advances time. A campaign ID determines its authoritative rules; a contradictory game argument is rejected. Layout and reading atmosphere remain independent presentation preferences.

## Evidence

The new browser matrix passed 7/7 checks across Original, Reclaimed Codex, The Orrery and Ember Ledger at 390/1100px, including real game/saved-campaign selection, independent commander displays, three-tab powers, personal/sovereign filters, domain choices, late responses and unchanged gameplay. This uses authenticated local transport and disposable campaigns, not a native ChatGPT acceptance run. Subsequent shared regression and publication evidence is recorded below when complete.

The base-phase resolver and progression are executable; arbitrary novel ability prose remains GM-adjudicated. Neither schema tests nor browser fixtures certify generated class quality, model prose, native phone behavior, campaign balance or a model latency percentage.

## Using the two games

Open the existing DnDGPT dashboard and choose **Game**. **Saved game** then contains only that game's campaigns. Switching changes no save, character, time or dice. **New campaign** sends the explicit new-game request to chat. Choosing a different game does not migrate an existing campaign. Each account still owns its campaigns in both games; filtering is a navigation boundary, with the existing account ownership checks protecting every read/write.

The existing `read_rules`, `create_chat_game`, `list_campaigns`, `get_campaign`, `save_chat_update` and `render_dashboard` tools handle both games. For a saved campaign, `read_rules(campaign_id=...)` derives the book from its saved identity. Before creation pass `game_id=sovereign-system` or `age-of-convergence`. Contradictory game/campaign arguments are rejected. Rules and the checklist are composed from shared source; the runtime does not ask a model to rewrite the manual. Both checklists fit one page, including compact response metadata. Cache by game and source hash; keep the game/campaign on subsequent pages.

The selected game/campaign is published to host model context without posting a chat message. This uses [the supported model-context mechanism](https://developers.openai.com/plugins/build/chatgpt-ui#keep-temporary-ui-state-in-the-ui) and widget-state compatibility. It is selection context, not a request to continue play. Ordinary progress and battle phases use the usual save; no separate sovereign read or battle tool is mandatory each turn. Actual thinking/narration time remains model-dependent.

## Progression and saves

Character growth follows the shared XP rules. Each gained level also awards one Sovereign Evolution credit. It upgrades an actually owned sovereign parent and has its own spending ledger, separate from quest credits and SP. General XP carries across thresholds of 100 + 50*(current level-1). Formation veterancy uses cumulative thresholds 0/100/250/450/700/1000. Domain advancement requires its finite, published milestone and one of three development choices. Force capacity is declared from the actual class and checked against the saved roster.

Standing orders have fictional start/due times, objectives and mandates. A due report requires actual adjudication and a recorded outcome; passing real time alone does nothing. Current snapshots keep the latest 50 full battle reports plus compact permanent retry receipts. Earlier full reports remain in save-history versions. Export/import retains game identity and sovereign state and restores a separate paused copy.

## Edited Intelligent UI prompt

[Copyable prompt](INTELLIGENT_STORY_UI_PROMPT.txt): 4,839 characters including its final newline. The added fix gives tooltip category, title, description and stats explicit separate rows, gaps, typography and wrapping while preserving the inline story trigger and full opaque four-sided border. The shared rulebook and both game checklists inherit the same instruction. Prompt delivery cannot prove that a future native generated tooltip renders correctly.
