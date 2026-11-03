# D&D 2024 mode and reusable characters

Approved direction: revised 2024 D&D, SRD 5.2.1; default for new campaigns. Existing Age of Convergence and Sovereign System saves retain their mechanics and identity, including legacy saves without a game ID.

## Current follow-up — adventure choice and explained creation

Runtime 1.1.2 removes the automatically selected adventure from new campaigns. Seven source-verified published adventures cover a classic Forgotten Realms dungeon, Innistrad gothic horror and siege warfare, whimsical magic, an arctic mystery, Barovian folk horror, Strixhaven comedy and festival puzzles. Original adventures are always offered. Existing selected adventures keep their IDs.

Guided creation uses two grouped replies: class and species together, then all remaining choices with recommended legal defaults. Quickplay stays one complete draft. Every choice gets a visible explanation of its use and benefit. list_dnd_options returns local class/species summaries, all eighteen skills' usual abilities and uses, background benefits and the grouped flow. Exact selected mechanics remain in the SRD references.

Published PDF sources are fetched automatically from fixed author/publisher URLs. The reader caches bytes/text, exposes logical section ranges, batches up to three sections and can return actual page images. Army of the Damned has image-only monster statistics; the Sheep Chase PDF has broken font encoding. Visual pages preserve access to that material instead of inventing missing rules or passing unreadable text. PDFium calls use a shared mutex because the library is not thread-safe; downloads are locked per source so unrelated books do not block each other. The source bytes and extracted text are not committed or included in player exports. Dependencies include PDFium's own notices through pypdfium2.

The follow-up passes **43 focused tests and 14 in-app browser checks**, including all four layouts at 375/768/1200px, the real Army selection message, choice explanations, selected-adventure status and unchanged fixture state. Additional picker checks at 375/768px find no horizontal overflow in any layout. All seven public sources were fetched successfully from the real network (0.85–3.82 seconds each in this local run). Army monster page 67 was visually inspected and its image-only statistics are readable. A Wild Sheep Chase returns actual source images instead of its damaged text encoding. These are source-access, instruction-delivery and simulated-host checks; they are not an end-to-end model campaign or model latency measurement.

**Published 1.1.2:** checked implementation `6a12c0ca94fbf1beff8f218668e56e7f8d40bd6f`; [feature CI](https://github.com/DeonHolo/DnDGPT/actions/runs/41563852796) and [main CI](https://github.com/DeonHolo/DnDGPT/actions/runs/41564216669) both pass **708 tests**, isolated hosted installation and packaging. Public health reports 1.1.2, the updated site is deployed, and anonymous campaign/MCP access returns 401. Native MCP returns all eight catalogue options, twelve class/nine species/eighteen skill explanations and the two-turn flow. All seven selected source sections succeed through that public connection, with source hashes matching the local real-network audit; Sheep Chase includes two actual image content blocks. The complete 6,145-character hardener matches SHA-256 `cfec3ffd6624df34032e0060dbfe8ab29ffe7c4ed0bdaa3293c94639aa39dccb`; the 5,618-character creation section is one page and matches guide SHA-256 `fafc0d17fdffb0608ce81d5884da71593e1d589eadc6af62e7cb612ed3c6df06`. The widget is 256,045 bytes before production-origin URLs. Reports and a picker screenshot are in ignored `dndgpt-app/test-results`. No production player campaign was edited and no ZIP uploaded.

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

Bundle the public SRD with its required attribution. Open5e data is filtered to the selected source and cached with provenance. The upstream MCP package declares MIT but omits a standalone LICENSE file; verify the notice before vendoring code. Frozen Sick remains one of seven published choices. New campaigns start without an adventure selection; the player chooses a published source or an original adventure. Fixed-URL, bounded HTTPS readers retrieve the chosen author/publisher HTML or PDF source and cache it in server memory. Chapter retrieval is model-only; source text is never placed in the dashboard, search or player export. The full adventure is not shipped in the repository. Original Forgotten Realms outlines and optional private packs remain available. Commercial sources are optional, not part of the normal setup.

## Latency

Load relevant sections, cache source entries, batch character/party updates into one transaction, and reuse the successful save response. No per-companion model calls or repeated whole-book reads. Report measured checks rather than a promised percentage speedup.

## Verification and remaining limits

- **Published 1.1.1:** checked implementation `d53b070fc8c7cc20f06c65a360c78d594b62b125`; [main CI 41458180141](https://github.com/DeonHolo/DnDGPT/actions/runs/41458180141) passes all **697 tests**, hosted-runtime installation and packaging. Public health reports 1.1.1 with D&D as default. Every one of the fifteen live backgrounds matches its local source hash and native dimensions; cache headers are preserved, and anonymous campaign/MCP requests return 401. The published site serves the free-starter/scenic copy. Native MCP returns the complete 5,750-character D&D hardener with matching SHA-256 `68bf35ea1dcf3908ed448a77ca3bac736d68c814c520b8804171881319ceebfa`. Browser/source/live reports and the starter screenshot are in the ignored local `dndgpt-app/test-results` directory. The widget is 255,579 bytes before production-origin URLs are added.

- Follow-up 1.1.1 passes **46 focused checks and 13 in-app browser checks**. The source reader fetched all ten official chapters in 0.902 seconds in a local real-network check; a second section read from memory took 0.000042 seconds. The UI test confirms that Play Frozen Sick submits its actual action, needs no upload, and keeps private GM content hidden. These timings exclude the model and hosted storage.
- Six packaging checks pass after including every catalogue artwork, nested D&D reference file, attribution and upstream notice in the optional source bundle. Runtime campaign data stays excluded. The user's hosted connection updates directly; no ZIP upload is part of play.

- The first complete passing CI run for the D&D implementation is [41392781209](https://github.com/DeonHolo/DnDGPT/actions/runs/41392781209), before the wallpaper follow-up. It covers source synchronization, an isolated hosted installation, the full Python suite and portable packaging.
- The wallpaper follow-up passes 37 focused D&D and scene tests, including owner isolation, separate game preferences, reference lookup, private adventure sources, reusable copies, arithmetic, import/export and real MCP transport. After separating original-resolution artwork, the widget HTML is 256,348 bytes, below 1,048,576 bytes. Additional checks exercise exact source bytes, original dimensions, caching, first-party CSP and denial of uncatalogued/private paths.
- The in-app browser passes 13 checks after the quality correction, including 375/768/1200px widths in all four layouts, companion sheets, search, library, game separation and read-only browsing. The original wallpaper check loaded all 15 prior images; the 1.1.1 rerun checks the 4000 × 1403 Dalelands original and a 1920px minimum for every replacement, and checks first-group order, copyright, availability and per-game selection.
- An 80-iteration local four-character normalization check had a median CPU time of 0.55 ms and a maximum of 1.09 ms. This excludes model generation, network and persistence; it is not a gameplay-turn latency measurement.
- Frozen Sick replaces the source-required Heroes of the Borderlands catalogue entry. A publisher outage or changed article layout returns an honest recoverable error with retry/original-adventure options. Its source is a live publisher reference with a response digest; private packs remain version-pinned. The published adventure predates the 2024 revision, so the guide explicitly identifies it as an adaptation using installed 2024 rules rather than claiming a newly published 2024 module.
- The server validates sheet structure, shared calculations, ownership, versions and state transitions. The GM still adjudicates legal choices, components, timing and situational rules. End-to-end model quickplay, long-campaign play and the physical Android app have not been measured here.
- No production player campaign was edited or advanced during implementation or testing. Tests use disposable local records and hosted-storage test doubles.
