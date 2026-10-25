# Combat rosters and Sovereignty — 1.0.49

Published 2026-10-25. Runtime commit: `12838a739e5d4f456a76045b22a7549338eb55ef`.

## Sovereign upgrades and repeated records

The previous view reused the regular ability inspector for Sovereign foundations and entity-owned capabilities. That produced Overview / Full rules / Upgrades inside an already acquired upgrade. It also displayed the class foundation in a separate box above the actual commander or formation. Those two presentations could look like duplicate forces even when the save contained one formation.

Each actual domain, commander and formation now has one record. **Earned upgrades** appears separately from **Core capabilities**. Acquired changes link to their real owner through the saved capability references; the same effect does not also appear as a second core ability. Each improvement shows its recorded name, rarity and change, with its current effect available in a disclosure. No default COMMON rarity is invented for a Sovereign upgrade. Regular player skills retain Overview, Full rules and Upgrades.

Current stats come from the actual entity. New saves preserve the genuine original foundation text before its first evolution. Existing original snapshots are retained. Older combined descriptions without an original snapshot remain a labeled foundation reference; they are not relabeled as a proven starting build. This release does not reconstruct player history or rewrite existing builds.

## Dashboard wording

Operation and battle outcomes use readable labels: `player_victory` displays as **Victory**. Common joined stat/time text is spaced for reading, including `Level1`, `HP43`, `DEF14`, `speed6m`, `over15min` and `per24hours`. Internal keys remain internal; the saved enum values and mechanics are unchanged.

## Allies & Combat

The active roster uses compact name / HP / status rows and one selected detail inspector. Explicitly related temporary summons can share a group while preserving each instance's HP and remaining rounds. Mouse, keyboard and search can select an individual actor. An actor does not need to be selected before search can find it.

Dead or explicitly ended enemies and temporary summons leave the active list and its count. A recoverable permanent companion at 0 HP remains visible as downed. Reading the roster does not spend fictional time, expire a surviving summon or mutate gameplay. The four layouts use the same responsive list and inspector.

## Was the casualty-history rejection correct?

Yes for protected Sovereign commander and formation records: the server requires retaining those entities and recording casualties/status. The rejection is not a blanket prohibition on removing transient enemy or summon rows. Their earlier versions and significant campaign-log outcomes preserve history.

Both games now route **roster-cleanup** to the full rule and include it in the hardener. The GM should reconcile resolved casualties and ended summons in the ordinary turn save, reuse stable IDs and preserve lasting or genuinely unexpired allies. Combat ending alone does not expire summons. During advancement, reconciliation cannot advance frozen time. This adds no separate cleanup save or recurring rules audit.

## Verification

- [CI 40199176719](https://github.com/DeonHolo/DnDGPT/actions/runs/40199176719): **659 passed**, two existing dependency warnings.
- Local focused checks: **96 passed** across roster/history, Sovereign progression, rule integrity/routing, resource size and the delivered script build.
- In-app browser: **83 passed** — 33 roster/Sovereignty, 19 search, 24 core player-view and 7 existing Sovereign flow checks. New geometry checks cover Original, Reclaimed Codex, The Orrery and Ember Ledger at 390, 800 and 1200 pixels. Pointer and keyboard inspection were also exercised. These are local simulated hosts, not an Android ChatGPT acceptance test.
- Hosted disposable probe: **22 hosting/public-connection + 15 recovery checks passed**; no real campaign accessed and no model generation benchmark.
- Public health reports **1.0.49**. Native MCP rulebook and hardener hashes match the released source for both games.
- Hardener lengths: Age **7,942**, Sovereign **7,993** characters; both return in one page. Dashboard resource: **1,035,403 bytes**, below the 1 MiB limit, with existing artwork retained. Scripts are compiled at build time; production requires no Node runtime.

Production deployment: `6ade09085a85d98e1ff4`. Private probe deployment: `6ade09068970e7173777`. Probe execution: `6ade096826abe27e40c3`.

No player save was edited, and no plugin ZIP was uploaded. Close and reopen an existing dashboard to load the new interface. Visual evidence in the workspace: `dndgpt-app/test-results/sovereignty-1.0.49.png` uses disposable sample values.
