# Sovereign progression review

Historical review of 1.3.1–1.3.2. The subsequent approved correction restores numbered levels, fourth-level rewards, complete starting bundles and the world introduction. Current design and release status: [creation and levels](SOVEREIGN_CREATION_AND_LEVELS_2026_11_05.md).

This records the current behavior, the requested selection correction, and the decisions still open. It is not a claim that numbered levels have been restored.

## What changed in the Laws overhaul

| Feature | Before the overhaul | Published Laws version 1.3.1 |
|---|---|---|
| Main class powers | Four substantial powers | Four powers, called Laws |
| STR / DEX / INT / CHA | Numerical attributes | Removed from this profile |
| Luck | Starting Luck and future rarity enhancement | Retained, score 1–20; no ordinary growth schedule defined |
| Random rarity | Six grades and independent acquisition rolls | Same table and Luck formula retained |
| Class rarity growth | Earned class evolution/ascension concept | A definite ascension route was not carried over |
| Class selection | Eight classes | Reduced to about three |
| Ordinary growth | Two core-power and two Sovereign upgrades per level | Two of each at a chapter breakthrough |
| Fourth-level bonus | One extra major refinement at 4/8/12… | Removed with numbered levels |
| Domain growth | Ordinary Sovereign upgrades plus a separate Domain checklist | One list of upgrades on the actual Domain |
| Bodies | Mobile, bound or distributed | All retained; no separate humanoid avatar required |
| Resolution | D20 checks and numerical combat machinery | One risky d6 maneuver exchange |

The technical tests established that the implemented save and tool paths worked. They did not establish preservation of the player's preferred progression features. The missing class-ascension instructions, Luck growth, numbered levels and fourth-level award were genuine omissions or design changes, rather than merely missing explanations.

## Requested selection correction

| Board | Offers | Selections |
|---|---:|---:|
| Class | 12 | 1 |
| Origin traits | 6 compatible strands of one origin | 2 |
| Titles | 6 compatible deed-based Titles | 2, or explicitly defer |
| Core-power upgrades | 6 distinct new applications | 2 |
| Sovereign upgrades | 6 enduring owner developments | 2 |
| Earned Origin/Title upgrades | 6 fitting developments | 2 on newly promised boards |

Ordinary story actions remain three to five choices, with typed/ordered actions supported. Explicitly delegated character generation remains available. Existing single-identity records and previously advertised one-pick quest rewards stay valid. New two-pick quest rewards name both picks explicitly. Choice counts are preferences, not a spendable currency. Future preference changes preserve issued boards, the actual creature, pause and time.

## The actual structure

```text
YOU — the creature, colony or bound being you chose
│
├── FOUR CORE POWERS (the book calls them Laws)
│   └── Core-power upgrades expand these powers
│       Example: a hunter can take root and become a place you act through
│
├── SOVEREIGNTY — Domain, General and forces
│   └── Sovereign upgrades permanently develop an actual owner
│       Example: a brood can establish and tend a living nursery on an expedition
│
├── ORIGIN — how you came to exist; chosen innate traits
│   └── Related discoveries/quests awaken new uses of those traits
│
└── TITLES — deeds and the capabilities earned through them
    └── Related deeds/quests develop the owned Title
```

Core powers can work through the creature's body, Domain or minions. The word personal did not mean that a bound tree must have a second walking body. Every core-power and Sovereign upgrade must open a materially new plan at its actual rarity. Numeric-only increases, cosmetic reskins and narrow conditional riders fail the offer check.

Origin and Title effects are additional mechanics, separate from the four main powers. In the current implementation their earned choices are conditional identity rewards, rather than automatically recurring level rewards. The GM presents earned choices in the story interface. The dashboard's Upgrades tabs show acquired history; Origin and Title histories live on their own Character & Progression cards. There is no unified automatic upgrade track covering all four groups.

## Current growth, after the count correction

```text
Creation → four core powers + two core upgrades + two Sovereign upgrades
           + two Origin traits + two Titles (unless deferred)
                      │
                      ▼
Chapter breakthrough → six core options / pick two
                       six Sovereign options / pick two
                      │
                      ▼
Related quest or deed → advertised Origin / Title / owner reward
                       six options / pick two on new identity boards
```

This is chapter progression. The correction does not restore numbered levels, per-level rewards, ordinary Luck growth or an automatic fourth-level bonus. Those decisions remain open after the player asked for an explanation of the different upgrade targets.

## Rarity: retained behavior and missing route

| Common | Uncommon | Rare | Epic | Legendary | Unique |
|---:|---:|---:|---:|---:|---:|
| 20% | 30% | 25% | 15% | 7% | 3% |

Every eligible new candidate has its own real roll. Luck grants a separate chance to promote that candidate one tier: 0% at Luck 5–6, 5% at 7–8, 10% at 9–10, rising to 35% at 19–20. Raising Luck changes future opportunities. An upgrade's rolled grade belongs to the upgrade; it does not automatically promote the source Class or reroll previously owned powers. The four class-native powers retain their source Class grade.

A clear class-ascension route and a predictable Luck-growth rule still need agreement. A concrete option to discuss is an announced, finite Ascension quest that advances the existing Class one tier and visibly broadens its four powers, without replacing the creature or its kit. This is a proposal, not implemented progression. Likewise, restoring two core/two Sovereign upgrades per numbered level and two extra major upgrades each fourth level has been proposed, but has not been accepted.

## Verification and published scope

Runtime **1.3.2**, tested implementation `fe39a3a9c0034a0174579e60c218defb01b66304`. The [isolated release run](https://github.com/DeonHolo/DnDGPT/actions/runs/42018223509) and [main run](https://github.com/DeonHolo/DnDGPT/actions/runs/42018591974) each passed **795 tests**, source synchronization, isolated hosted imports and packaging. New cases exercise twelve genuinely independent rarity draws, complete six-option/two-pick boards, paired mechanical identities through authenticated start and portable restore, a promised two-pick identity quest reward paid once, and a future preference change during a pause. Previously issued boards snapshot their own counts; changing future preferences does not reinterpret those old choices or charge a currency. That compatibility decision is enforced in `dndgpt-app/app/sovereign_laws.py` and its focused tests.

The in-app browser passed seven checks with real local authenticated MCP transport and disposable SQLite campaigns: both Origin traits and Titles, the collapsible progression guide and story, four core inspectors with all three tabs, actual Domain/force capabilities, search without fetching state again, all four layouts at 390/1100px, and no saved-version change from browsing. This was a simulated host, not an Android or native ChatGPT playtest. Evidence is local `dndgpt-app/test-results/sovereign-laws-browser.json`.

At **2026-11-05 11:28 UTC**, public health reported 1.3.2 and the hosted application dashboard matched the tested source byte for byte after excluding exactly one hosting-injected Cloudflare analytics script. The published site has the corrected counts. Anonymous campaign/MCP requests return 401. The actual connected MCP returned the complete 5,161-character hardener and 1,138-character compatible index. Source hashes: hardener `aad311d2ca975e3d59c1ac5c4c2514021205349a64f4534fdfd7ae36dad51e2e`; book/index `33e09af6ca95938f698477ef2d83938a0a0c4e599bd063493918ec13bfcc919b`. Local reports are `sovereign-laws-public-1.3.2.json` and `sovereign-laws-native-1.3.2.json` under `dndgpt-app/test-results/`.

No player campaign was opened, changed or converted, and no ZIP was uploaded. Technical tests do not prove that every generated class is enjoyable or that the GM follows all instructions in a long campaign. The progression omissions described above remain open; this release does not silently restore levels or introduce a new ascension system.
