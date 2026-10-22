# Rulebook wording review — 23 October 2026

The reported seven-panel duplication had a source-level cause: Chapter 38 required exactly seven collapsible HUD sections in **every** gameplay response. Older instructions in Chapter 33, creation, final restrictions and `PRESENTATION.md` repeated that requirement. Newer companion instructions put the same information in the connected dashboard. Asking for “Intelligent UI” could therefore select conflicting instructions.

## Resolved wording conflicts

| Finding | Clarification |
| --- | --- |
| Intelligent UI meant both the story and the full HUD. | Intelligent Story UI is the in-chat narrative, dialogue, inline glossary, campaign palette, compact results and working choices. The separate dashboard owns seven full chapters. This scope applies throughout the book. |
| Closing or losing the dashboard could trigger a full chat copy. | Hidden, closed or unavailable dashboard does not request a copy. A full chat sheet requires an explicit FULL HUD / full character sheet request and applies to that request only. The ordinary interaction fallback stays compact. |
| Seven collapsible panels conflicted with actual chapter navigation. | Real dashboard navigation with one full chapter visible satisfies the seven-chapter architecture. Collapsible layouts remain valid; chat does not duplicate either layout. |
| Ability instructions named Mechanics / Upgrades / Appearance instead of the required tabs. | Preserve Overview / Full rules / Upgrades. Flavor stays with the overview, and acquired upgrades remain under their exact parent. |
| A small glossary card was also told to show complete ability rules. | Inline hover/tap/focus gives concise known information. Full ability mechanics remain in the inspector or a requested detail answer. |
| Tooltip text required dark, thin-bordered cards while the newer contract allowed adaptive themes and required a complete opaque border. | Both specifications now require opaque, readable cards with a continuous contrasting solid border on all four sides, at least 1.5px, preferably 2px. Light and dark campaign palettes remain valid. |
| “Five phases” could be confused with five creation turns. | Four choice turns sit within preparation phases A-E. Clarification messages do not consume a fixed message allowance. Character confirmation and adventure authorization stay separate. |
| “No saving or loading operation” sounded like a ban on automatic server saves. | No manual save/load ritual or unsolicited downloadable checkpoint. Connected tools save authorized outcomes automatically; disconnected chat cannot claim external durability. |
| GM setup and chat-led documentation described `world` updates as wholesale replacement. | Ordinary world objects merge recursively, as the implementation already does. Lists/scalars and specified replacement objects still replace; reviewed corrections retain their existing behavior. |
| A display example mislabeled a source rarity and used measured reach despite current presentation rules. | Distinguish the unchanged Common source from its Rare evolution. Describe reach to the player while retaining the original 6m source for adjudication. |

## Scope and validation

Reviewed the competing presentation directives, section routing, creation sequence, ability display, tooltip specification, continuity/persistence and final GM instructions. This is a wording and instruction-consistency review, not a balance redesign or proof of model compliance in every conversation.

The canonical rulebook, compact hardener, presentation guide, generated rule index and portable GM references are synchronized. The recorded revision is reversible so unrelated source preservation can be checked. No character, roll, resource, acquisition rule, approval gate or saved campaign is migrated. No additional routine model call, dashboard render or save-verification read is introduced.

The hardener is 7,913 characters and routine `story-ui` is 6,040 characters, each fitting one existing 8,000-character response. All 36 focused local checks passed, covering pagination, source integrity, reference synchronization, packaging and standard character rules. These checks validate the delivered instructions; a new uncoached live gameplay evaluation is still separate evidence. Existing chats must retrieve the revised rules before the new wording can guide their next response.
