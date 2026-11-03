# Choose a game before loading its rules

Update: 1.1.5 removes the extra dashboard resource bindings described below. Only render_dashboard opens a component; ordinary calls update it. See DASHBOARD_OPEN_ONCE_2026_11_03.md.

Runtime 1.1.4 adds a neutral DnDGPT entry. Calling the connection without a named mode or specifically targeted save returns a short introduction to D&D 2024, Age of Convergence and Sovereign System. ChatGPT asks which the player wants. The dashboard presents the same three choices. An explicit mode or a named saved campaign opens directly.

## Delivery

- `render_dashboard` is the instructed first entry call. Its response contains the introduction and mode choices, so opening and asking do not require separate rule or campaign reads.
- `read_rules`, `list_campaigns` and `create_chat_game` also return the chooser when their game is omitted. No campaign is created, book loaded or dice rolled in that branch. An existing save never selects a mode for an unspecified request.
- These entry tools and `get_campaign` advertise the same modern MCP Apps resource and legacy ChatGPT output template as `render_dashboard`. Routine saves, rolls and reference lookups do not acquire a dashboard binding. Existing OAuth scopes and app-only execution controls remain.
- The UI ignores a stale game in widget state. A neutral tool response clears the displayed campaign. Explicit choices filter saves by game and share the chosen context. The mode cards send the actual named choice to chat; dropdown browsing alone remains a view selection.
- Existing in-flight request guards prevent an old response from undoing a newly selected mode. No server-global “first call” flag is used: the stateless server cannot identify a ChatGPT chat or read its natural-language prompt reliably. The caller supplies the named mode/campaign and follows the first-entry instruction.
- This changes launch behavior, not saved campaign identity. Ongoing play reuses its established campaign and mounted dashboard without an extra render or mode question each turn.

## Verification

The in-app browser passed 6/6 launch checks using a simulated legacy bridge and real authenticated local MCP with disposable saves. They cover stale widget state, all three introductions, no unchosen book, actual choice submission, explicit-mode bypass and unchanged campaign/audit records. All four layouts were checked at 375, 768 and 1,100 pixels. The revised Sovereign dashboard passed 8/8 regression checks; D&D passed 14/14. The final pass also checks that returning from Ember Ledger to the neutral chooser hides the old chapter rail and preserves the available width. Twelve focused server/transport checks passed, including all new entry cases and existing archive/library regressions. The first local attempt hit a locked, reused Windows pytest temporary directory; a fresh per-run `--basetemp` completed successfully without deleting or moving the existing directory.

Published runtime commit `20f1ec9224ac144ae4e159642734d157d5958e0f` passed **733 tests**, bundled-rule checks, the isolated hosted runtime and portable packaging in [feature CI](https://github.com/DeonHolo/DnDGPT/actions/runs/41579938669). [Main CI](https://github.com/DeonHolo/DnDGPT/actions/runs/41580213520) and the site deployment also passed. At 2026-11-03 04:51 UTC, public health returned 1.1.4 with `default_game_id=null`; the complete hosted dashboard matched the local tested bytes (SHA-256 `ad10a5617fa299cc1fb8b355c441a5cae1256aa9731478f1ccab7a4b90c4fed8`). The site showed the three-mode launch instructions and four-power Sovereign description. Anonymous campaign and MCP requests remained 401. Evidence is in local `test-results/modes-release-public-1.1.4.json`, the browser reports and `mode-chooser-1.1.4.png`.

The browser checks prove the component and transport behavior. They do not prove that every ChatGPT model follows the first-tool instruction, or that a particular Android host opens the component. Display remains controlled by the host; the server supplies both supported resource bindings.
