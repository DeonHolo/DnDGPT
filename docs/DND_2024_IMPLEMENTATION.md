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

The Reading atmosphere dropdown groups 33 shared choices separately from three official D&D artworks: Silver Dragon Jubilee, The Frozen North and Ravenloft — Lord Soth. The latter group is visible only in D&D mode. Each game remembers its own selection through the existing preferences save, without an additional gameplay call. Official artwork keeps its source, artist and Wizards copyright notice. Background encodings were reduced to keep the self-contained widget below ChatGPT's 1 MiB resource limit; original copies are kept outside the repository.

## Resource boundaries

Bundle the public SRD with its required attribution. Open5e data is filtered to the selected source and cached with provenance. The upstream MCP package declares MIT but omits a standalone LICENSE file; verify the notice before vendoring code. Published commercial adventures require an accessible authorised source before a playable pack can be prepared. A catalogue entry alone must not claim to contain a full adventure.

## Latency

Load relevant sections, cache source entries, batch character/party updates into one transaction, and reuse the successful save response. No per-companion model calls or repeated whole-book reads. Report measured checks rather than a promised percentage speedup.

## Verification and remaining limits

- The first complete passing CI run for the D&D implementation is [41392781209](https://github.com/DeonHolo/DnDGPT/actions/runs/41392781209), before the wallpaper follow-up. It covers source synchronization, an isolated hosted installation, the full Python suite and portable packaging.
- The wallpaper follow-up passes 37 focused D&D and scene tests, including owner isolation, separate game preferences, reference lookup, private adventure sources, reusable copies, arithmetic, import/export and real MCP transport. The embedded widget is 1,028,207 bytes after rebuilding, below 1,048,576 bytes.
- The in-app browser passed 12 checks before the wallpaper additions, including 375/768/1200px widths in all four layouts, companion sheets, search, library, game separation and read-only browsing. A thirteenth check now exercises official wallpaper grouping, copyright, availability and per-game selection. Record its actual browser result before claiming it passed.
- An 80-iteration local four-character normalization check had a median CPU time of 0.55 ms and a maximum of 1.09 ms. This excludes model generation, network and persistence; it is not a gameplay-turn latency measurement.
- Heroes of the Borderlands is a source-required catalogue entry. Its commercial adventure text is not bundled. An authorised prepared pack must be supplied before running that published module. Original adventures can be prepared as private outlines, using the included Forgotten Realms source links for setting context.
- The server validates sheet structure, shared calculations, ownership, versions and state transitions. The GM still adjudicates legal choices, components, timing and situational rules. End-to-end model quickplay, long-campaign play and the physical Android app have not been measured here.
- No production player campaign was edited or advanced during implementation or testing. Tests use disposable local records and hosted-storage test doubles.
