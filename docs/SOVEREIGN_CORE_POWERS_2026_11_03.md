# Sovereign core powers — 3 November 2026

The approved direction is a small set of personal powers that develop throughout play. Ordinary levels and rewards deepen the existing kit. Rarity, real combat timing and permanent sovereignty growth remain.

## Result

- Four substantial personal powers by default. A fifth requires a specific class-design reason recorded during creation; rarity alone adds no slots.
- No mandatory Active/Passive/Reaction/Free Action/Utility kit or dashboard grouping. Each power still defines its actual uses, timing, costs and responses.
- The third creation turn offers five refinements, choosing two, in place of two new standalone Signatures. Title and Background benefits attach inside real parents. The free starting permanent Sovereign upgrade stays separate.
- Each character level grants two personal refinements automatically, alongside one permanent Sovereign upgrade and the ordinary attribute allocation. Every fourth level preserves an additional major personal refinement. Banking remains voluntary.
- Normal personal progression only upgrades owned powers. Extra standalone personal powers require an explicit player request and its recorded exception. Gear, commanders, formations and entity-owned abilities retain their separate acquisition paths.
- A single named list opens Overview, Full rules and Upgrades. Current rules are consolidated; history preserves each improvement's actual rarity and source. Search opens the correct power/tab.

## Persistence and compatibility

`personal_powers` is a server-owned allowance/history record. A new campaign starts with two creation selections; actual level gains add the level and fourth-level awards once. `spend_personal_upgrades=[{ability_id,upgrade_id},...]` is committed in the existing `save_chat_update` together with the new nested children and changed combined rules. Availability, prior children, source rarity, double funding and duplicate spending are checked. Two improvements to one parent can share one save. Retries use the existing owner/version/action protections.

Quest-funded refinements retain `spend_evolution_credit`; personal and permanent Sovereign funding cannot pay the same child. The existing quest validator requires a single new child for its selected parent; combine different parents in one batch or resolve same-parent quest/personal funding sequentially. Ordinary power use and status updates spend no refinement.

Existing characters retain their entire actual kit and history. Only actual unspent Skill/Talent points carry over, once, on an ordinary authorized save. No retrospective awards for spent points or old levels. Read-only views and preference-only saves cause no migration, time passage or resource changes. An explicitly requested consolidation uses the existing reviewed correction path and saved history. No production character is rewritten by deployment.

## Rules composition

Age of Convergence's source remains untouched (SHA-256 `94ec7b0882418a00fc6140c09fa725984be02aaa3d70f9cf7664fcb55399a529`). Sovereign replaces only reviewed creation, personal progression and presentation selections. `rules/sovereign/personal/manifest.json` pins each selected source section's hash; composition fails closed if it changes. The reversible replacement audit can reconstruct the shared source. This avoids asking the GM to reconcile old Talent/Signature instructions with a contradictory appended note.

The indexed `sovereign-personal` contract is under one 8,000-character tool page. Reuse it and the saved parents; no new tool or per-power lookup is required. Personal, Sovereign and normal turn changes share the normal batched save. No whole-turn model latency claim is made.

## UI and validation

Use existing responsive reading-layout controls, full names, visible selection, keyboard-operated detail tabs, and touch-sized rows. The ui-ux-pro-max focused disclosure searches returned an unrelated heading result and no relevant pattern on retry; its general accessibility and responsive guidelines are used as fallback. No new visual system or decorative motion is introduced.

Implementation and focused/browser/full release verification are recorded as checks complete. Schema checks cannot certify the creativity or balance of a generated class, and rule delivery is not proof that every future model reply follows it.

Focused verification: 97 affected checks passed across the initial run and corrected follow-up. The first run caught a missing portable-state allowlist entry, a test-only dialogue spelling, and a collected fixture still using the retired six-slot kit. The archive allowlist and fixtures were fixed; all five follow-up checks, including paid-refinement restore and frozen/custom behavior, pass. Full CI then caught a fixture persisting computed `personal_progression` into raw state: that field belongs only to the public view, so the fixture strips it, while the authoritative `personal_powers` ledger remains portable. Eight in-app Sovereign checks pass, including every layout at 375/768/1100px, retained detail tabs, search and unchanged disposable game state.

Published with the neutral mode chooser in **1.1.4**, runtime commit `20f1ec9224ac144ae4e159642734d157d5958e0f`. [Release CI](https://github.com/DeonHolo/DnDGPT/actions/runs/41579938669) passed all **733 tests**, rule synchronization, isolated hosted-runtime checks and packaging; main CI passed too. The final browser runs passed 8/8 Sovereign, 14/14 D&D and 6/6 mode-launch checks. At 2026-11-03 04:51 UTC the public runtime reported 1.1.4 and its full dashboard matched the tested local bytes. See [launch verification](MODE_SELECTION_2026_11_03.md) for the public report and scope. No ZIP was uploaded and no live campaign was read or changed for verification.
