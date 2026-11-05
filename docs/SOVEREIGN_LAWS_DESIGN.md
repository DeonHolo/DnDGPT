# Sovereign Laws design notes

5 November 2026. Approved design and implementation for the Sovereign Laws playtest.

## Agreed direction

- Build play around a creature and the laws that govern what it can do. Allow mobile, bound and distributed forms with distinct ways to act, sense and be threatened. Let the GM derive each domain from its creature and setting. Roots, reflections, tide pools and built gates all belong where the fiction supports them.
- Resolve a whole risky maneuver with real dice, including the sovereign's action, allied follow-through and the opposition's response. State the achievable effect and visible stakes before the roll. Retire variable DCs, measured movement, the default MP and cooldown template, and individual attack rolls for minions. Fictional reach, injuries and costs determine what is possible.
- Give Generals and forces distinctive capabilities and behavior. Keep the names, actual location, standing orders, condition and consequences that affect play. Scale the force to its nature and purpose. Routine upkeep follows established orders in the background. Bring decisions forward when the player has a meaningful choice.
- Make earned upgrades open new plans. Rarity determines how far the new possibility reaches. Personal upgrades develop an existing Law. Sovereign developments permanently change the Domain, General or forces where the improvement takes effect. Existing powers can be used creatively in the moment.
- Use Origin for how a creature came to be. Let Titles arise from witnessed deeds and earned reputation. Both should give playable benefits and have a way to grow. The identity story and the actual acquired effect belong together in Character & Progression.
- Shorten the opening. Start from the creature the player asked to be, offer distinct ways it can play, and include the actual kit and starting developments in the draft. A player who wants to choose every detail can use the detailed builder. Open on a situation that gives the chosen creature something interesting to do.
- Give hunts and conquests distinct threats, observable enemy plans and real endings. Honor action-focused play. Close objectives, deliver the promised rewards, and show what changes when the player returns. A surviving enemy can act on what it learned.
- Fit equipment and trophies to the actual body and its allies. Replace the mandatory equipment slot count with objects or installations that have a clear use. The player can decide where a meaningful trophy belongs when more than one use makes sense.

## Origin and Title progression

An **Origin** gives an inherent capability when chosen. A major discovery about what made the creature can awaken a lasting change in that same trait. For a tree born inside a drowned ferry, **Wreckborn** lets its roots take hold in waterlogged timber. When it recovers the missing half of its first hull, it could awaken **Hollow Hull**, which lets it grow a sealed, breathable chamber inside any wreck it has rooted into. The new shelter changes what the creature can do during a flood, a rescue or a siege.

A **Title** gives an earned act shaped by the deed. **Netbreaker** could be a name given by people who saw the Orchard free its young from a dredger's net. Its roots can open physical restraints they touch while keeping the captive safe. After the Orchard frees someone from an enchanted prison, a later development could let it turn a magical binding on the jailer by touching the anchor. The deed grounds the permission. The witnesses and the spread of the story determine who recognizes the name.

Try one growing Origin trait and one power-bearing Title in the first playtest. Other names can matter as reputation. Grade the acquired capability by rarity. An identity earns new growth at a turning point in the adventure. If other upgrades are due, present the choices together. Track the current effect and the deed or discovery behind it in the usual save.

## One Domain upgrade path

The current rules give regular Sovereign developments at creation and on character level gains. The player can spend one on the Domain, General or forces. The Domain also has its own milestone with two to six objectives. Finishing it raises Domain level and awards one of three developments. Both routes can grant a permanent Domain capability.

Use one list of Domain upgrades in the redesign. A regular Sovereign choice or an explicit reward for a major accomplishment can add to that list. A quest can promise a Domain upgrade and award it when the quest closes. Its objectives come from the actual situation. Retire the mandatory Domain level checklist.

Record territorial changes as soon as the action achieves them. Rooting into the captured shoal gives the Orchard reach at that shoal. Learning to take root in floating reeds changes where it can grow anywhere it meets that condition. The first is a new holding. The second is a repeatable capability and belongs in Domain upgrades. When an accomplishment earns both, record each once in the same save.

## First playtest

Use an Orchard and a very different creature such as a being that lives in reflections. Give both the same short rescue or hunt and see if their bodies, forces and gear produce different plans. Complete the objective, pay out one real reward, and play a subsequent scene where the earned change matters.

Start with one real d6 roll per risky maneuver. On 1–2 the threat gains the upper hand and the scene changes. On 3–4 the intent succeeds with a concrete consequence. On 5–6 it succeeds cleanly. Clear advantage uses two dice and the higher result. A clear advantage for the opposition uses the lower result. Use the ordinary batched roll and save path. Tune the roll bands and the frequency of identity awakenings after the playtest.

## Implementation and compatibility

New Sovereign campaigns select `sovereign-laws-2026-11-05`. The canonical book and one-page hardener live in `dndgpt-app/rules/sovereign/laws/`. Connected rule reads route by the saved campaign profile; the plugin carries matching offline copies. The archived embodied profile remains available for compatibility. Publishing and reading do not convert or modify existing player campaigns. D&D and Age of Convergence retain their own rules.

The save validator accepts creature capabilities, four Laws, Origin, Title, actual Domain holdings and named allies. Its creation checks use those records. Maneuver receipts record the genuine dice, kept result and outcome band; retries reuse the same receipt. Quest rewards can promise a development for its named scope. Applying it requires the completed quest and records the source once on the owner. The existing atomic save, version check, ownership, pause and reviewed correction protections remain.

The dashboard displays native capability records and each owner's earned history. Laws keep Overview, Full rules and Upgrades; Your story stays collapsible. Gear records its actual holder or place. All four layouts use the same records. Search uses the mounted campaign without another tool call.

This release adds no model judge or simulation call per turn. Ordinary risky play uses one roll call and one batched saved outcome, with already loaded rules and current state reused. This describes the intended call path, not measured end-to-end ChatGPT latency or proof of long-campaign story quality.

## Verification

The focused backend checks passed 13 cases: mobile/bound/distributed creation, all outcome bands and both edge directions, retry reuse, incomplete-start protection, Origin/Title quest rewards, duplicate-award rejection, archive restore, authenticated rule routing, and batching a maneuver with an independent contextual roll in one receipt/save. The older Sovereign, personal power and direct-play suites passed all 125 cases. Those tests use disposable campaigns.

The in-app browser passed seven checks using a local simulated host and real authenticated MCP transport: Origin/Title and collapsed story, four Law inspectors, actual Domain/force capabilities, gear search without a tool call, ally search, all four layouts at 390/1100px, and unchanged saved versions while browsing. Evidence is in the local `dndgpt-app/test-results/sovereign-laws-browser.json`. These checks do not establish native ChatGPT rendering or actual Android app behavior. A full played campaign remains the next story-quality test.
