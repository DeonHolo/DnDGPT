# Presentation layer — DnDGPT

This guide controls presentation only. The complete edition-1.0 rulebook and hardener retain mechanical authority. It does not create powers, change rules, authorize gameplay or guarantee a particular native ChatGPT layout.

Power descriptions use complete readable mechanics from the first creation offer. Show descriptive reach and concrete movement/targeting choices in chat kits, summon stat blocks, Full rules and upgrades. Counted meters, feet, paces, steps or other distance units belong only in private source mechanics or an explicitly requested spatial audit. Preserve all other stats, costs, dice, durations and action limits; changing the presentation never changes legal range or movement.

The dashboard is player-facing. Render curated game facts rather than enumerating saved keys. Omit zero costs/cooldowns, inapplicable values, bookkeeping booleans, source/type/status/group fields, parent IDs, formulas and preparation enums. Preserve depleted HP/charges at zero and actual restrictions. Choose one readable rules representation; never show Mechanics and Mechanics display as separate copies. Upgrades uses `change_display` for additions/changes only, with the combined ability under Full rules. The renderer also filters existing records without mutating saves; no campaign migration is needed for this presentation cleanup.

## Player-facing name and rules

Use **DnDGPT** alone in launch cards, headings and prompts. Omit software/rulebook versions and retired subtitles. Internal version fields, file names and rule-precedence records remain unchanged; disclose them only when the player asks. This naming preference applies to newly generated native Chat UI as well as the hosted dashboard.

Describe the game as a heavily customized, D&D-inspired fantasy RPG built around Deon Holo's preferences, with its own rules, classes and progression. The full GM plugin includes the complete rulebook and Rule Hardener. A hosted custom MCP connection can fetch the same standard texts through `read_rules`; file uploads are only needed for custom forks or a genuinely unavailable rules source.

## Native Intelligent UI in regular Chat

Use genuine native controls when the client supports them. Guide the model through these preferences; do not describe them as a CSS theme or component-registration API.

- Lead with the scene/result and three to five meaningful choices. Each choice has a short intent label and one brief descriptive sentence explaining the approach and relevant known cost, risk or opportunity. Keep conditions readable without repeating whole ability descriptions. Keep ordered custom actions available. Choices express an intention in chat; an intention is not an approved database mutation.
- Use polished, genuinely clickable event/action cards inspired by the readable hierarchy of a Slay the Spire event screen: original non-emoji vector/line iconography, action-led titles, crisp type hierarchy, comfortable spacing and brief consequential cost/risk lines. Highlight key terms and values with meaningful host-supported accents while preserving the established resource, rarity and readiness palette and neutral action-economy labels. Keep text equivalents, strong contrast, keyboard focus, touch access and unclipped narrow-screen layouts. Avoid emoji substitutes, plain numbered menus when native controls work, rainbow prose and decorative metadata. Preserve required offer counts and confirmation gates; custom ordered actions remain available. Full rules and the hardener define the complete native event/action card contract.
- Use a compact character strip: identity/level/class, labeled HP/MP, XP, and the important current condition or ally status. HP is red and MP blue; always retain text values and labels.
- Retain exactly these seven collapsible HUD groups, in this order, initially collapsed on ordinary gameplay responses unless the player requests otherwise:
  1. Character & Progression
  2. Skills & Class Abilities
  3. Health & Conditions
  4. Allies & Combat
  5. Equipment & Inventory
  6. Quest Journal
  7. World & Campaign Log
- Inside Skills, group combat actions/commands, defensive/off-turn reactions, standalone passives and exploration/utility. In the connected dashboard, select an ability from a compact index and read Overview or Full rules in one inspector. Keep complete conditions, integrated evolutions and Imprints with their parent. Use short metadata labels instead of explanatory tag paragraphs. World uses an article index; Campaign Log uses a searchable timeline. Do not add a casting button for a passive child.
- Prefer clear hierarchy, breathing room, short summaries, restrained host-compatible accents and explicit rarity/READY/ACTIVE/COOLDOWN/UNAVAILABLE/SPENT labels. Avoid oversized decorative headings, repeated prose, raw Markdown markers and unreadable color-only indicators.
- Inspection and expansion are view operations: no rolls, time, resource spending, quest changes or automatic actions. Opening a progression panel does not spend points or resume play. Actual level-up retains the rulebook's advancement UI and freeze requirements.
- Restyling, recoloring, adding icons and redisplaying are also view operations. Keep proposed effects and narrated-but-unsaved events distinct from committed outcomes, and never replay an action to make a presentation revision. Supported native icons and typography are preferences; do not invent styling APIs, fetch unrelated art or generate unrequested images to imitate them.
- Use the latest authoritative engine snapshot when connected. Distinguish proposed effects from committed outcomes. If tools are disconnected or mechanics are unfinished, say so; a polished display is not a saved game.
- Exact native layouts may vary. If real controls are unavailable, explain the limitation and use the source's compact text commands. Do not render a static imitation while calling its headings clickable.

## Companion view

The companion covers the same seven information groups, not seven individual statistics. It complements the conversation rather than moving narration to another model backend. The user requested a tabletop fantasy design with navigation buttons opening full detail pages, replacing top-level collapsible cards in this companion only. Retain each group's short summary on its button; Character & Progression includes level and XP. Keep the seven groups in canonical order and show one full chapter page at a time. Ability, evolution and Imprint expanders remain nested inside Skills. This does not change the native Chat HUD contract above or any preserved rule text.

Use the custom visual system in DESIGN_SYSTEM.md: parchment/obsidian surfaces, brass accents, serif headings, inline SVG and labeled resource meters. A vertical rail fits wide views; a compact navigation grid fits narrow views. Keep selected-page and nested-detail state across refresh. Chapter navigation is local and never requires a new AI response. The existing `panels` preference stores the selected chapter as its first entry; this is presentation state, not campaign state.

Author HTML/CSS only inside the MCP App. Follow host typography, theme variables, safe areas, keyboard focus and narrow-screen constraints. Do not style ChatGPT's outer interface or fake floating PiP with fixed-position page elements. Report the actual granted host mode.

On the tested regular-Chat desktop client, both standard and compatibility PiP requests returned/stayed inline. Use a usable inline companion by default until an actual floating view is demonstrated. Keep floating support a separately recorded capability, not a requirement for native narration or durable data.

The same client also exposed **Open app in tab**. That opened an app pane beside Chat, with host-reported mode `fullscreen`. The dummy view kept the same iframe instance, local interaction status and advancing server clock through another completed Chat reply and conversation scrolling. Prefer this tested companion-pane path for a constant interface; do not call it PiP or infer cross-session persistence. Codex's general browser pane is another place to display a website, but opening a URL there alone does not connect it to chat.

When the player explicitly chooses to keep the HUD in a connected companion, use the rulebook's existing HUD-hiding preference to avoid repeating its full details in every chat reply. Keep native narration and meaningful action choices in the conversation, and keep the seven complete groups in the companion. A disconnected display must not pretend it knows fresh game facts. This is a presentation preference, not a rewrite of the preserved rules.

MCP App message delivery triggered an assistant acknowledgment without a separate visible user message in the measured client. Label a control's intended action accurately and retain a prompt-copy fallback when delivery fails. Never claim it has the same visible-message behavior as the native UI without testing it.

Core facts, ownership and at-most-once commits belong in the authenticated engine/database. Widget state and expansion preferences are presentation caches. Normal play does not require manual save/load rituals or generated checkpoint downloads.

## Saved detail formats

Keep generated headings and journal summaries short: a useful title or one sentence, with full outcomes and mechanics in the entry's detail fields. Never repeat the entire campaign checkpoint as a heading or current-scene summary. Retain complete acquired mechanics; compact presentation is not permission to omit restrictions or invent missing costs.

The companion separates Allies / Combat, Equipment / Inventory and World / Campaign Log into local subtabs. A summon starts with identity, HP, defense and movement; Combat & instincts, Nature & interior, Evolution and Recovery & permanence expand independently. Evolution ranks expand separately. World facts, nested preparation records and log entries use labeled details rather than flattened object dumps. Log headings are capped at100 characters while full saved text stays available. Character background/class/talent/biography, conditions, items, supplies and quests follow the same structured detail convention.

Chat-led abilities can store `effect`, `cost` and `ready`; development-engine abilities can store `mechanics`, numeric resource costs and explicit `status`. Display the actual saved fields from either format. Absent numeric costs do not imply free activation; absent engine status does not imply UNAVAILABLE. Creation abilities are marked DRAFT, and an activation beginning with Passive belongs under Passives even when it includes preparation instructions. Do not rewrite saved abilities to repair their display.
