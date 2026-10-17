# What kind of RPG is DnDGPT?

Recommended public wording: **a standalone, D&D-inspired d20 RPG built as a substantial system hack for ChatGPT**.

“Hack” and “homebrew” overlap in community usage. The practical distinction for a new player is whether they can bring a standard 5e character and use the normal books directly. DnDGPT replaces enough of that framework that conversion is required. Calling it only “5e homebrew” can suggest a compatible class, subclass or extra-content collection; calling it “5e compatible” would overstate what this project supports.

| Area | Standard D&D 5e | DnDGPT |
| --- | --- | --- |
| Attributes | Six ability scores | STR, AGI, INT, CHA and LCK |
| Modifier baseline | Scores of 10–11 give +0 | `floor((Attribute − 5) / 2)` |
| Magic economy | Spell levels and spell slots | MP and individually specified powers |
| Classes and progression | Published class progressions | Rarity-generated original class kits, Signatures, Talents and integrated evolution |
| Shared foundations | d20 checks, advantage/disadvantage, attacks and reactions | Related d20 conventions, with custom numerical scales and action rules |

These observations come from `dndgpt-app/rules/rulebook-v1.0.txt`, especially Attributes, Classes and Heroic Power, Checks and Combat. A shared d20 convention alone does not prove derivation from a particular 5e edition. The repository does not document a comprehensive SRD compatibility target, so the README uses **D&D-inspired system hack**, rather than claiming exact 5e compatibility or a formal classification.

The earlier blanket choice of “homebrew, not hack” was too narrow. A game can be homebrewed and also be a hack. Google AI Overview's “homebrew is always 100% compatible” and “zero learning curve” claims are likewise too absolute. There is no percentage calculation used here to decide the label; this is an editorial description based on the rules above.

## Sources checked

- [Official D&D rules: Playing the Game](https://www.dndbeyond.com/sources/dnd/br-2024/playing-the-game): the six abilities, modifiers and D20 Tests.
- [Official D&D 5e spellcasting rules](https://www.dndbeyond.com/sources/dnd/basic-rules-2014/spellcasting): spell levels and spell slots.
- [The 5E Hack, by its creators](https://www.hotheadcollective.com/the-5e-hack/): an explicitly described 5e hack with stated design goals; its [rulebook](https://www.hotheadcollective.com/content/files/2024/02/THE-5E-HACK.pdf) relies on 5e for unchanged rules.
- [Nimble's creator updates](https://nimble5e.backerkit.com/hosted_preorders/project_updates): the creator distinguishes the original modular 5e rules from developing a standalone system.
- [D&D Beyond's homebrew guidelines](https://dndbeyond-support.wizards.com/hc/en-us/articles/7747193843092-Homebrew-Rules-and-Guidelines): the platform's use of homebrew for custom content, not a universal taxonomy of game systems.

Research checked 18 October 2026. The wording is a reasoned comparison, not an official certification or a compatibility test.
