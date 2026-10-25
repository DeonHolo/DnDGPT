# Campaign focus and dialogue

Both games support campaign-owned preferences. Choose in the existing World Preview or change them later by asking your GM. New and unconfigured campaigns default to Mixed with Normal dialogue; existing saves are not rewritten on publication.

| Preference | Choices |
| --- | --- |
| Adventure focus | Mixed; Hunt & Explore; Conquest |
| Dialogue | Normal; Minimal; On request |

Sovereign Mixed defaults to **70% personal adventure / 30% strategy**. Conquest can center warfare and expansion. Hunt & Explore centers expeditions. Age of Convergence uses the same focus choices through the character's actual capabilities.

Minimal dialogue provides short essential exchanges and actionable information through scouting, tracks, maps, discoveries and reports. On request summarizes routine exchanges and reserves direct dialogue for player requests. Both provide direct action routes without mandatory negotiations or council/interview chains. NPC agency, known consequences, geography and existing commitments remain real.

Hunts and conquests have finite objective checklists, declared System rewards and concrete benefits. Completed objectives stay completed; counterattacks are new objectives. Authorized personnel handle routine upkeep. Approaches use actual skills, upgrades, gear, summons and forces.

Open **World & Campaign Log → Objectives** to inspect preferences, active objectives, rewards, expected benefits, changed places and known Sovereign fronts. Preference controls send your request to chat; the GM saves it. The Saved label shows the committed selection, not unsaved control values.

Examples:

- “Use Hunt & Explore with Minimal dialogue for this campaign.”
- “Switch this Sovereign campaign to Conquest. Dialogue on request.”

## Save contract

Use the existing `save_chat_update` changes object:

```json
{"campaign_preferences":{"focus":"conquest","dialogue":"on-request"}}
```

`focus` accepts `mixed`, `hunt-explore`, `conquest`. `dialogue` accepts `normal`, `minimal`, `on-request`. Fields merge independently. Preferences travel in full, turn and resume views and portable exports. A preferences-only save is permitted during a manual pause or advancement freeze and changes neither time, build, pending decisions nor the pause. Normal ownership, version and exact-retry guards apply.

Structured quests can additionally record `activity` (`hunt` or `conquest`), `target`, `known_opposition` and `victory_benefit`. Reuse existing objective/reward settlement and `life_updates` for earned aftermath. Preferences add no routine tool, rules read, artificial combat or automatic gameplay action.

These are GM instructions and persistent preferences. Backend tests establish save/transport behavior; they do not certify how consistently a particular model follows the adventure style.
