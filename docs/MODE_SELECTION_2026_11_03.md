# Choose a game before loading its rules

Runtime 1.1.4 adds a neutral DnDGPT entry. Calling the connection without a named mode or specifically targeted save returns a short introduction to D&D 2024, Age of Convergence and Sovereign System. ChatGPT asks which the player wants. The dashboard presents the same three choices. An explicit mode or a named saved campaign opens directly.

## Delivery

- `render_dashboard` is the instructed first entry call. Its response contains the introduction and mode choices, so opening and asking do not require separate rule or campaign reads.
- `read_rules`, `list_campaigns` and `create_chat_game` also return the chooser when their game is omitted. No campaign is created, book loaded or dice rolled in that branch. An existing save never selects a mode for an unspecified request.
- These entry tools and `get_campaign` advertise the same modern MCP Apps resource and legacy ChatGPT output template as `render_dashboard`. Routine saves, rolls and reference lookups do not acquire a dashboard binding. Existing OAuth scopes and app-only execution controls remain.
- The UI ignores a stale game in widget state. A neutral tool response clears the displayed campaign. Explicit choices filter saves by game and share the chosen context. The mode cards send the actual named choice to chat; dropdown browsing alone remains a view selection.
- Existing in-flight request guards prevent an old response from undoing a newly selected mode. No server-global “first call” flag is used: the stateless server cannot identify a ChatGPT chat or read its natural-language prompt reliably. The caller supplies the named mode/campaign and follows the first-entry instruction.
- This changes launch behavior, not saved campaign identity. Ongoing play reuses its established campaign and mounted dashboard without an extra render or mode question each turn.

## Verification

The in-app browser passed 6/6 launch checks using a simulated legacy bridge and real authenticated local MCP with disposable saves. They cover stale widget state, all three introductions, no unchosen book, actual choice submission, explicit-mode bypass and unchanged campaign/audit records. All four layouts were checked at 375, 768 and 1,100 pixels. The revised Sovereign dashboard passed 8/8 regression checks; D&D passed 14/14. Twelve focused server/transport checks passed, including all new entry cases and existing archive/library regressions. The first local attempt hit a locked, reused Windows pytest temporary directory; a fresh per-run `--basetemp` completed successfully without deleting or moving the existing directory. Full CI/publication results follow after completion.

The browser checks prove the component and transport behavior. They do not prove that every ChatGPT model follows the first-tool instruction, or that a particular Android host opens the component. Display remains controlled by the host; the server supplies both supported resource bindings.
