# Character confirmation recovery

The pending confirmation was stored against the current save version, but was older than the 15-minute approval window. `pending_approval` filtered expired proposals out, so refreshing the dashboard could not display a control or explain the expiry. Comparing the renderer before and after layout integration found no removed element IDs or named functions; the expiry filter predates the layouts.

## Change

- Return the current-version proposal after expiry with an expiry status, without its approval token.
- Display **Review again**. That click creates a fresh, validated preview; a separate **Confirm character** click commits it. Starting the adventure remains a separate approval.
- Keep approval outside the hideable codex, and clear it when the campaign or save version changes.
- Read both direct and nested ChatGPT compatibility metadata.
- Keep the server's 15-minute expiry, owner checks, version checks and app-only execution unchanged.

## Verification

- Full Python suite: 433 passed, with two existing dependency warnings.
- Added hosted-storage expiry coverage after that run; targeted storage, approval and package checks: 27 passed.
- Real local MCP transport tests cover expired reads, token isolation, fresh previews, unchanged state/history during review, stale drafts, owner isolation, and separate character/adventure gates.
- JavaScript syntax checks passed. Static comparison to `7e4561b` found no removed element IDs or named functions. This does not establish browser behavior.
- Browser tests are prepared in `dndgpt-app/tests/approvals.html` for all four layouts at 375, 700 and 1100 pixels, reload, compatibility metadata and one-time confirmation. Execution is pending: the browser tool reported **Local browser use is disabled in Work settings**.
- The affected live campaign was read only. No character confirmation, adventure start, correction, roll or campaign write was performed.

## Release status

Candidate dashboard: 1.0.28. Candidate plugin: 1.0.33. Deployment and private-plugin publication have not yet been verified.
