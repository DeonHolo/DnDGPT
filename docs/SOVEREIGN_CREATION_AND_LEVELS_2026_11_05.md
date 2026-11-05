# Sovereign creation and levels

Approved follow-up to the 1.3.2 enjoyment audit, 5 November 2026. Implementation target: 1.4.0. Publication evidence follows verification.

## Creation

The generated setting uses Age of Convergence lore. An introduction explains contact between Earth and other worlds, how communities adapted, and the specific HOW/WHERE of the starting region's Earth connection. This comes before Class cards. Save public lore in `world.summary` and `world.earth_connection`; keep hidden causes private. An explicit different setting remains possible.

The guided order is:

1. World/story introduction, followed by twelve Class offers, choosing one. The introduction can share the first reply with those cards.
2. Six Core upgrades, choosing two, and six Sovereign upgrades, choosing two, shown together.
3. Six Title and six compatible Origin choices, choosing two from each, with explicit Title deferral allowed.
4. Fitting gear, a supplied or editable proposed name, Your story and the opening. These can accompany the final identity choices without another approval turn.

Four core powers remain. The base Domain, General and forces do not consume the two opening Sovereign developments. Creation readiness now checks the actual acquired Core and Sovereign upgrades on their owners. New drafts also require their saved introduction and connection; Class rarity generation waits for that world context. Existing active saves are not retroactively blocked or rebuilt.

There is no compulsory vulnerability field or routine vulnerability row in the current Sovereign dashboard. Creature functions describe how it acts. Special weaknesses can be part of an explicitly chosen concept. The rules discourage invented fuel costs, preparation chores and buying back ordinary creative applications of an existing power. Power and upgrade descriptions state effects and actual changes, with brief flavor and relevant triggers.

## Numbered progression

| Reaching a level | Regular Core upgrades | Permanent Sovereign upgrades | Extra major Core refinements |
|---|---:|---:|---:|
| 2, 3, 5, 6, 7, 9… | 2 | 2 | 0 |
| 4, 8, 12, 16… | 2 | 2 | 2 |

Each board offers six choices, choosing two. Major refinements use the Class's grade. The ordinary candidates keep their genuine independent rarity rolls. Powers develop new capabilities on their actual owners. Origin and Title improvements are additional earned quest/deed rewards.

Use milestone levels, without an XP grind or fixed objective count. Announce the next concrete level goal in the Quest Journal and close it when its real finish line is achieved, including through an effective shortcut. A Class-ascension quest can separately grant one Class tier and two class-grade refinements. The server raises all four class-native Law grades together while preserving old upgrade grades/history. At UNIQUE, the Class remains UNIQUE and the two exceptional refinements remain owed.

Luck is internal background rarity machinery. New native characters start at 9 and gain 1 per earned level, capped at 20. There is no allocation choice, dashboard statistic, reward line or narration about it. Native rarity calls use the saved value, even if a caller supplies another value; they can omit it. Earlier recorded scores and roll receipts are preserved. The six base rarity chances and existing one-tier enhancement formula are unchanged. This does not affect maneuver dice.

## Reward settlement and owed choices

The existing once-only quest settlement handles the new fields. `system_reward.level_up=true` normalizes to `{core_picks:2,sovereign_picks:2,major_picks:2}`; an explicit object preserves custom promised counts. Closing the quest grants one level and background growth atomically. The settlement records its level, regular selections and the major selections actually due. `class_ascension=true` normalizes to `{picks:2}` and grants the next Class grade plus those refinement selections. The two reward types can coincide. Keep standalone `development` packages separate.

Selected owner upgrades use `source=quest:ID`. Core, major and ascension children use `award_kind=core|major|ascension`; Domain/General/forces use their actual owner. The validator checks each source/category's promised selections. This is an owed reward history, not a player currency or token wallet. The dashboard shows pending choices by their actual earned source, and removes them from that reminder as they are applied. A level milestone's character updates are server-controlled within that payout, preventing the caller from adding them twice. Retries reuse the committed result.

## Rolls and pacing

Keep the d6 bands and edge rules. Before a maneuver, declare the uncertainty, effect, stakes and facts already certain. Optional `effect`, `stakes` and `established` fields preserve those declarations on the existing roll receipt. A poor die can decide that a commander escapes; it cannot turn weak guards into army-killers or undo an already assured capture. A mixed success delivers its intended objective and a proportionate consequence within the declared stakes. Routine or decisive actions can happen without a roll. These rules constrain GM narration; storing the declaration does not prove every generated reply obeys it.

The GM chooses a useful scene scale around the player's intent. There is no 70/30 ratio or mandatory personal-adventure quota. Batch routine logistics and repetitive actions. Surprise checks now include meaningful domain activity, defense and hunts, with at most one check per material transition. The same 10/30/50/70% chances apply. Discoveries, opportunities and unusual creatures are valid outcomes alongside danger. Reuse the same roll batch and saved outcome, without a new per-turn tool loop.

## Source separation and compatibility

Current Sovereign has its own compact book/hardener and section index. Archived homebrew operating instructions moved out of the active GM wrapper into `references/legacy-game-master.md`, loaded only for those profiles. D&D and Age of Convergence retain their canonical rule sources. Existing campaigns keep their selected game/profile and actual acquired history. Publishing does not open or migrate player campaigns.

## Verification status

Focused native tests pass 27 cases, including complete starting awards, world-before-Class generation, server-scoped rarity, levels 2/3/4 with actual selected regular/major/Sovereign upgrades, once-only reward retries, source-budget rejection, Class ascension preserving history, combined level/UNIQUE refinement rewards, capped internal growth, pre-existing active-save compatibility, declared maneuver scope and portable restoration. Full regression, in-app browser and public release evidence are recorded after those checks complete. The tests use disposable campaigns, not live player saves.
