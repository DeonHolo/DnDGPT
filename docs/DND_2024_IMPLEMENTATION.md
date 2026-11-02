# D&D 2024 mode and reusable characters

Approved direction: revised 2024 D&D, SRD 5.2.1; default for new campaigns. Existing Age of Convergence and Sovereign System saves retain their mechanics and identity, including legacy saves without a game ID.

## Delivery plan

- [x] Independent six-attribute character/party schema, character library and versioned campaign copies.
- [x] Complete quickplay draft instructions and controls, ordinary chat start/revisions, companions with full sheets.
- [x] Official SRD reference, source-restricted Open5e lookup and evaluation of heffrey78/dnd-mcp reuse.
- [x] Private adventure library: prepared-pack import, original Forgotten Realms adventures, section retrieval and progress.
- [x] Official-sheet-inspired responsive character page, library, party and spell/resource views.
- [ ] Transport, storage, mechanics and browser regression checks across all three games and four layouts.
- [ ] Release documentation and verification; record any unavailable published source explicitly.

## Save boundaries

Character library versions are reusable snapshots. Campaigns own independent live party copies. Adventures hold GM reference material separately from player-visible progress. Source secrets never enter widget metadata, search or portable player exports.

## UI direction

Use the official 2024 character sheet as a structural reference: identity strip; six clearly labelled ability boxes with modifiers, saves and skills; combat vitals, attacks and features; separate spellcasting and inventory areas. Build original HTML/CSS, with restrained ink, paper, outlined fields and burgundy accents. Preserve theme/layout choices and readable mobile stacking. Do not embed a scaled-down PDF or add decorative motion.

The ui-ux-pro-max design-system search produced generic marketing patterns; those are not adopted. Its verified form-label, mobile typography and submission-feedback guidance applies. Use system fonts, visible focus, 44px controls, unclipped content and explicit loading/error/success feedback.

Later user refinements: the D&D feature inspector keeps Overview and Full rules, with a conditional Level progression tab populated from actual source level changes. Spells retain At Higher Levels text. The redundant action composer and Send to chat button are removed from every game's dashboard; the conversation remains the gameplay input.

## Resource boundaries

Bundle the public SRD with its required attribution. Open5e data is filtered to the selected source and cached with provenance. The upstream MCP package declares MIT but omits a standalone LICENSE file; verify the notice before vendoring code. Published commercial adventures require an accessible authorised source before a playable pack can be prepared. A catalogue entry alone must not claim to contain a full adventure.

## Latency

Load relevant sections, cache source entries, batch character/party updates into one transaction, and reuse the successful save response. No per-companion model calls or repeated whole-book reads. Report measured checks rather than a promised percentage speedup.
