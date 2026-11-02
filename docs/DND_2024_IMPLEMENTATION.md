# D&D 2024 mode and reusable characters

Approved direction: revised 2024 D&D, SRD 5.2.1; default for new campaigns. Existing Age of Convergence and Sovereign System saves retain their mechanics and identity, including legacy saves without a game ID.

## Delivery plan

- [x] Independent six-attribute character/party schema, character library and versioned campaign copies.
- [x] Complete quickplay draft instructions and controls, ordinary chat start/revisions, companions with full sheets.
- [x] Official SRD reference, source-restricted Open5e lookup and evaluation of heffrey78/dnd-mcp reuse.
- [x] Private adventure library: prepared-pack import, original Forgotten Realms adventures, section retrieval and progress.
- [x] Official-sheet-inspired responsive character page, library, party and spell/resource views.
- [x] Transport, storage, mechanics and browser regression checks across all three games and four layouts.
- [x] Release documentation and verification for 1.1.0; follow-up 1.1.1 checks recorded below.

## Save boundaries

Character library versions are reusable snapshots. Campaigns own independent live party copies. Adventures hold GM reference material separately from player-visible progress. Source secrets never enter widget metadata, search or portable player exports.

## UI direction

Use the official 2024 character sheet as a structural reference: identity strip; six clearly labelled ability boxes with modifiers, saves and skills; combat vitals, attacks and features; separate spellcasting and inventory areas. Build original HTML/CSS, with restrained ink, paper, outlined fields and burgundy accents. Preserve theme/layout choices and readable mobile stacking. Do not embed a scaled-down PDF or add decorative motion.

The ui-ux-pro-max design-system search produced generic marketing patterns; those are not adopted. Its verified form-label, mobile typography and submission-feedback guidance applies. Use system fonts, visible focus, 44px controls, unclipped content and explicit loading/error/success feedback.

Later user refinements: the D&D feature inspector keeps Overview and Full rules, with a conditional Level progression tab populated from actual source level changes. Spells retain At Higher Levels text. The redundant action composer and Send to chat button are removed from every game's dashboard; the conversation remains the gameplay input.

The Reading atmosphere dropdown keeps 33 shared choices and a first, D&D-only group of 15 text-free scenic views. The selection covers the Dalelands, Calimport, Baldur’s Gate, Moonshae Isles and a haunted Ravenloft bastion. It includes one full panorama and separately published artist detail views, rather than fifteen different places. Original image widths range from 1,920 to 4,000 pixels. Artist, source and Wizards copyright remain in the credits.

The earlier compressed preview and then branded wallpapers were rejected. They have been replaced with original scenic image files, preserved byte for byte. The ten shared images reduced during earlier work were restored. Only the selected background loads, separately from the compact MCP resource. Content-hashed URLs and immutable caching avoid repeated downloads. The public route serves only catalogue artwork; campaign and Gallery data remain authenticated. The MCP CSP permits static assets from the configured server origin. This adds no model/tool call.

## Resource boundaries

Bundle the public SRD with its required attribution. Open5e data is filtered to the selected source and cached with provenance. The upstream MCP package declares MIT but omits a standalone LICENSE file; verify the notice before vendoring code. Frozen Sick is the ready-to-play default, set in Wildemount, levels 1–3. New campaigns reference it directly without an owned pack. A fixed-URL, bounded HTTPS reader extracts only the official public adventure article and caches it in server memory. Chapter retrieval is model-only; source text is never placed in the dashboard, search or player export. The full adventure is not shipped in the repository. Original Forgotten Realms outlines and optional private packs remain available. Commercial sources are optional, not part of the normal setup.

## Latency

Load relevant sections, cache source entries, batch character/party updates into one transaction, and reuse the successful save response. No per-companion model calls or repeated whole-book reads. Report measured checks rather than a promised percentage speedup.

## Verification and remaining limits

- Follow-up 1.1.1 passes **46 focused checks and 13 in-app browser checks**. The source reader fetched all ten official chapters in 0.902 seconds in a local real-network check; a second section read from memory took 0.000042 seconds. The UI test confirms that Play Frozen Sick submits its actual action, needs no upload, and keeps private GM content hidden. These timings exclude the model and hosted storage.
- Six packaging checks pass after including every catalogue artwork, nested D&D reference file, attribution and upstream notice in the optional source bundle. Runtime campaign data stays excluded. The user's hosted connection updates directly; no ZIP upload is part of play.

- The first complete passing CI run for the D&D implementation is [41392781209](https://github.com/DeonHolo/DnDGPT/actions/runs/41392781209), before the wallpaper follow-up. It covers source synchronization, an isolated hosted installation, the full Python suite and portable packaging.
- The wallpaper follow-up passes 37 focused D&D and scene tests, including owner isolation, separate game preferences, reference lookup, private adventure sources, reusable copies, arithmetic, import/export and real MCP transport. After separating original-resolution artwork, the widget HTML is 256,348 bytes, below 1,048,576 bytes. Additional checks exercise exact source bytes, original dimensions, caching, first-party CSP and denial of uncatalogued/private paths.
- The in-app browser passes 13 checks after the quality correction, including 375/768/1200px widths in all four layouts, companion sheets, search, library, game separation and read-only browsing. The original wallpaper check loaded all 15 prior images; the 1.1.1 rerun checks the 4000 × 1403 Dalelands original and a 1920px minimum for every replacement, and checks first-group order, copyright, availability and per-game selection.
- An 80-iteration local four-character normalization check had a median CPU time of 0.55 ms and a maximum of 1.09 ms. This excludes model generation, network and persistence; it is not a gameplay-turn latency measurement.
- Frozen Sick replaces the source-required Heroes of the Borderlands catalogue entry. A publisher outage or changed article layout returns an honest recoverable error with retry/original-adventure options. Its source is a live publisher reference with a response digest; private packs remain version-pinned. The published adventure predates the 2024 revision, so the guide explicitly identifies it as an adaptation using installed 2024 rules rather than claiming a newly published 2024 module.
- The server validates sheet structure, shared calculations, ownership, versions and state transitions. The GM still adjudicates legal choices, components, timing and situational rules. End-to-end model quickplay, long-campaign play and the physical Android app have not been measured here.
- No production player campaign was edited or advanced during implementation or testing. Tests use disposable local records and hosted-storage test doubles.
