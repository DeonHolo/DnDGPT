# Skill and ability hardening — edition1.0

User-authorized revision,2026-10-16. This extends the existing Class novelty check to ability generation across Class powers, Signatures, Titles, Background Imprints, Skill Evolutions, Talent Web offers/keystones, Class Breakthroughs/Grand Signatures and earned summon/item powers.

The main new firewall is in Section9 of the complete rulebook, with explicit links in Sections19–21 and a compact companion-hardener Section3A. It requires concise pre-roll concept screening, stripped-name mechanical comparison, at least three meaningful play directions on a five-offer board, practical current-build use, honest tier strength and comparison with actually available generation records.

Generic damage-subtraction and small conditional movement bonuses may each be the main identity of at most one offer per board. Neither is mandatory. These are repeated-filler ceilings, not bans on defense, mobility, simple useful Common/Uncommon effects or previously defined Stage benefits. Novel defensive/traversal laws can coexist. The text does not prescribe a menu of replacement abilities that would become the next recurring template.

Acquisition rules remain separate: Skill Evolutions/Imprints stay integrated in their real parent; Talents remain separately acquired with optional open/synergy/keystone paths; milestones retain fixed class-grade3+2 structure and their single Background-synergy slot. No extra boards, points, actions, rarity rolls or player turns are added. Existing saves, acquired powers and revealed offers are not migrated or buffed by this edit.

Preservation is reversible at byte level. `rules/skill-originality-v1.0.json` contains the exact authorized insertions. `scripts/apply_rule_amendment.py` inserts bytes without newline normalization. Removing only those insertions restores the prior complete edition1.0 files; reversing the original edition-label substitutions then reproduces the original supplied file hashes. Tests retain both proofs and verify packaged copies. Historical archives and the currently running verified snapshot are separate from the new working sources.

These checks prove source integrity and packaging, not that every future ChatGPT offer will be creative. Real generated boards must still be judged by their actual mechanics. The first-play implementation remains ChatGPT as GM plus reusable rolls and persistent saved dashboard data, as described in `CHAT_LED_PLAY.md`; this rule revision does not require a full executable rules engine.
