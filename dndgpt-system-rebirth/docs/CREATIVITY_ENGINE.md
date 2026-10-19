# Class variety and writing craft

## Skill direction and world context

The October 19 revision adds a comparison of trigger, operation, payoff and limits. Point-marking and repeated-hit echoes count as repeated mechanical families even when their names change. The GM should consider different player decisions before naming a power, then check the finished kit against the current board and available campaign history. Reactions can attack or disrupt; Utility can be Active or Passive. The starting region must be described before Class generation so specialized abilities have ordinary uses in the world the player is entering.

This is generation guidance, not a new catalog or a claim of guaranteed novelty. It preserves rarity rolls and existing owned powers. The revision is recorded in `dndgpt-app/rules/generation-breadth-and-world-2026-10-19.json`; integrity checks reverse it before verifying the previous source.

Research informing this design:

- [Prompting Diverse Ideas: Increasing AI Idea Variance](https://arxiv.org/abs/2402.01727) studies how prompting affects the spread of generated ideas. Applying its broad lesson here is a design inference: compare distinct mechanical directions before selecting finished offers. The study does not establish that this game prompt produces original abilities.
- [Fate Core's Building Stunts](https://fate-srd.com/fate-core/building-stunts) distinguishes new permitted actions, bonuses and bounded rules exceptions, and warns against abilities whose conditions rarely occur. Those distinctions inform the design questions and ordinary-use audit; no Fate mechanics or example abilities were copied.
- [D&D's rules glossary](https://www.dndbeyond.com/sources/dnd/br-2024/rules-glossary#Reaction) defines Reaction through timing and a trigger. DnDGPT keeps its own action budget and mechanics; a defensive role is not inherent in the word Reaction.

The existing rules already required a first-board novelty audit and 12–15 brief seeds before five Class offers. More fantasy adjectives did not address the reported repetition: bell/choir imagery, negated-word titles, and powers explained through unrealized futures. These are semantic habits; changing a noun leaves the underlying habit intact.

## What changed

The complete rulebook and Rule Hardener now require:

1. Establish the player's activity, source, changed state, limitation and counterplay before naming a class.
2. Compare the five finalists by actual decisions and interaction. Reconstruct overlapping engines instead of renaming them.
3. Check the last two accessible Class boards and the player's stated taste. Track recurring image families and title structures, including synonyms. Never claim access to unavailable campaign history.
4. Name the completed concept from its concrete identity. Conceptual and temporal powers still need observable triggers, precise effects and counterplay.
5. Critique the completed board from the player's perspective before displaying it. Keep exploration concise; elaborate only the finalists. Preserve independent rarity rolls, published offers and the four-turn creation process.
6. Use grounded action, distinct NPC voices, appropriate pacing and the viewpoint's actual knowledge during narration. Leave player decisions to the player.

This is guidance for the GM model. Passing an automatic class-kit count check does not prove a concept is creative. Playtesting fresh boards is still needed to assess the effect, and old owned classes are not rewritten by reading the new rules.

## Repository reviewed

Reviewed [haowjy/creative-writing-skills](https://github.com/haowjy/creative-writing-skills) on 18 October 2026 at commit `340b6838c961c9e87e63dfb12a5d8d56b080ad1f`, including its skill inventory, README, license and the relevant source files:

| Source | Useful idea for DnDGPT |
| --- | --- |
| [creative-writing-muse](https://github.com/haowjy/creative-writing-skills/blob/main/cw/skills/creative-writing-muse/SKILL.md) | Separate exploration, drafting and critique while retaining the author's intent. |
| [llm-writing](https://github.com/haowjy/creative-writing-skills/blob/main/cw/skills/llm-writing/SKILL.md) | Revise language deliberately rather than accepting habitual phrasing. |
| [writing-principles](https://github.com/haowjy/creative-writing-skills/blob/main/cw/skills/writing-principles/SKILL.md) | Balance clarity, discovery and character behavior. |
| [scene-construction](https://github.com/haowjy/creative-writing-skills/blob/main/cw/skills/creative-writing-craft/resources/scene-construction.md) | Distinct speech and scene pacing. |
| [failure-modes](https://github.com/haowjy/creative-writing-skills/blob/main/cw/skills/writing-principles/resources/failure-modes.md) | Diagnose repetitive voice, exposition and inflated intensity. |
| [reader-sim](https://github.com/haowjy/creative-writing-skills/blob/main/cw/skills/reader-sim/SKILL.md) | Review the experience from the recipient's perspective. |

The upstream project uses [Apache-2.0](https://github.com/haowjy/creative-writing-skills/blob/main/LICENSE). No upstream skill files, agents, project setup or memory tooling were copied into DnDGPT. The amendment is independently written for this game's class generation and narration; these links acknowledge the workflow inspiration. Players need only DnDGPT, not an extra writing plugin. No service, API key or additional model call was added.

The additive revision is recorded in `dndgpt-app/rules/class-diversity-and-craft-2026-10-18.json`. Integrity checks reverse the insertion and verify the preceding source exactly. The rulebook's gameplay-facing edition label remains Version 1.0.

## Opening world introduction

The World Bible already explains that Earth and other realms became connected through stable gateways and physically merged lands, followed by disruption, adaptation and established exchange. The new Turn 1 introduction requirement brings that existing context into the player's first response: a brief historical bridge, the present region and Earth's relevance, then the character's still-open origin and possible adventures. It keeps the actual cause of the Convergence separate from public history and preserves the Luck stop gate. A new player need not infer the premise from an unexplained setting name.

This additional insertion is tracked by `dndgpt-app/rules/world-introduction-2026-10-18.json`. It uses the existing Layered Canon rather than creating a universal date, mandatory Earth origin or compulsory portal-arrival story.
