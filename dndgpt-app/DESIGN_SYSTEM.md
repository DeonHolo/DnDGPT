# DnDGPT companion — visual system

User-directed tabletop fantasy dashboard, edition 1.0. Presentation only; source rules and game state remain authoritative elsewhere.

## Direction and provenance

Applied the user-requested `ui-ux-pro-max` skill. Its verified UX search, `navigation selected page keyboard`, returned Active State, Keyboard Navigation and Skip Links. These inform the implementation.

The initial design-system query returned generic SaaS defaults. The one narrower retry, `gaming RPG`, matched Gaming but suggested neon colors, 3D effects and a marketing showcase. That visual preset does not fit this fast, embedded tabletop companion and was not adopted or persisted as an approved preset. The fantasy palette, serif headings, d20 crest and codex layout below are custom design decisions; accessibility and responsive guidance come from the skill.

Stack: existing standalone HTML, CSS and vanilla JavaScript. No framework, external font, image or animation dependency was added.

## Layout and navigation

- One persistent character/resource strip above the codex.
- Seven navigation buttons in canonical rulebook order, each with its own current summary. Character & Progression includes level and XP.
- One full chapter page visible at a time. The other pages remain mounted, preserving nested detail state.
- From 620 CSS pixels: vertical navigation rail and detail page alongside it. Below 620: two-column navigation grid above the page. The seventh button spans the row.
- Visible selected treatment plus `aria-current="page"` and `aria-controls`. Tab/Enter/Space work normally; arrow keys, Home and End move through chapters. A skip link reaches the content.
- Navigation is local. It sends no chat message, rolls no dice and performs no game action. The authenticated app may debounce a presentation-preference write; the public dummy probe has no database.
- Reuse the existing preference schema: `panels[0]` stores the selected chapter, defaulting to Character. Older multi-panel preferences select the first valid entry. Nested `details` preferences remain independent. No database migration is needed.

## Visual tokens

| Role | Light | Dark |
|---|---|---|
| Surround | `#f0e9d9` | `#111610` |
| Page | `#fff9eb` | `#192018` |
| Inset | `#e9dfca` | `#1d241c` |
| Text | `#302a1f` | `#f1e7d1` |
| Secondary text | `#665940` | `#c0b49b` |
| Brass accent | `#79551c` | `#dfbb70` |
| Control border | `#8d7959` | `#9b8863` |

HP remains red, MP blue and STA green, with labels and numeric values. XP has its own labeled brass meter. Status and rarity retain explicit text.

Georgia/system serif headings evoke a character sheet; system sans keeps controls readable. Base size is 16px, ordinary page copy 14.4px, navigation summaries at least 12px. Spacing uses 8/12/16/20/24/30px. Use subtle borders, small corners and restrained shadows; avoid heavy textures, imagery and constant animation.

All structural icons are inline SVG with consistent strokes and decorative semantics beside visible labels. Brand imagery is not implied. Host light/dark selection and safe areas remain supported. Hover/focus/press feedback does not move layout; reduced-motion disables transitions.

## Verification boundaries

Equipment & Inventory uses a two-tab subnavigation within its existing chapter. Equipment shows worn/wielded items, grouped across occupied slots by item ID, plus compact empty slots. Inventory shows stored important items and a compact supplies ledger. Item summaries expose recorded name, rarity and short context; native details/summary reveal only recorded public fields. Missing data is labeled rather than generated. Hidden rarity receipts are excluded, and text enters the DOM through textContent.

Skills & Class Abilities now uses four subtabs: Combat, Reactions, Passives and Utility. Each shows its owned ability count and one group page at a time, with the full canonical group title retained inside. Evolutions and Imprints stay nested under their actual parent and never inflate standalone-passive counts. All four pages remain mounted; switching preserves expanded details. The row wraps into two columns in a narrow chapter and uses four columns when the chapter has at least 420px of content width.

Skill tabs expose tablist/tab/tabpanel semantics, one selected tab and roving focus. Left/Right wrap, Home/End select the first/last group, and modifier shortcuts pass through. The optional skills_tab presentation preference stores combat/reactions/passives/utility independently of equipment_tab. Legacy preference records default to Combat. No game state, clock, roll or chat message changes when switching groups. The targeted ui-ux-pro-max query returned relevant keyboard navigation, accessible-name and horizontal-overflow guidance; the codex visual tokens remain the existing custom design.

Tab/Enter/Space and Left/Right/Home/End work with tablist/tab/tabpanel semantics and roving focus. The optional equipment_tab preference stores selection while old preference records remain valid. Detail expansions remain separate; inspection changes presentation preferences only.

View options contains saved-game selection, manual refresh and hide controls; Connection details contains technical versions and receipts. Sandbox Review shortcuts and sandbox creation stay inside collapsed Development tools, clearly separate from eventual gameplay choices. The character strip retains Saved/check feedback and visible connection-loss warnings. A decorative initial badge was removed after the user found it ambiguous.

The targeted skill query for inventory disclosure returned touch guidance; its one narrower accordion retry returned unrelated typography guidance. Neither result establishes accordion-specific advice. The implementation reuses the existing semantic HTML details pattern and applies the previously verified keyboard, target-size, contrast and responsive rules.

The browser harness checks every chapter, current-page semantics, keyboard behavior, 340/480/640/1024px overflow, selected-page and nested-detail restoration, source-backed summaries/meters, representative text/border contrast in both themes and unchanged game state during inspection. Existing at-most-once approval tests remain required.

These checks do not constitute a complete accessibility audit or prove production OAuth, saved-state synchronization, floating PiP or cross-session client persistence. Record actual ChatGPT preview acceptance separately in `CLIENT_ACCEPTANCE.md`.
