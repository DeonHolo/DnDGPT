# Search and Gallery release — 2026-10-25

Published runtime **1.0.48**, commit `4c5fd73d5222637fab4642792544b62465bf0fc0`.

## Changes

- A search bar below Saved game finds player-facing text in the selected campaign. Results open the matching panel, ability detail, parent Upgrades tab, item, archived quest, older log entry or Sovereignty record. Loaded Gallery labels are searchable. Typing and showing more matches make no server/model calls.
- Fixed the public storage connection in 1.0.47. Diagnostics showed `401 api_key_invalid` for the public domain's injected credential; internal executions passed. A dedicated secret variable now provides the same record-storage access. OAuth, ownership checks and transaction/version rules remain enforced.
- The generated-image tool still declares the documented `openai/fileParams` schema. The art prompt was not the cause of this service-wide storage failure.
- Compacted the delivered dashboard modules to **1,042,264 bytes**, below the existing 1 MB limit. Maintainers retain readable sources, a pinned build command and a source-hash check. Hosting requires no Node/npm runtime.

## Verification

- [CI 40177269748](https://github.com/DeonHolo/DnDGPT/actions/runs/40177269748): **650 passed**, two existing dependency warnings.
- In-app Chromium with disposable host fixtures: **65 passed** — 19 search, 24 player-view, 14 living-campaign, 8 quest/Gallery checks. Search exercised Original, Reclaimed Codex, The Orrery and Ember Ledger at 390/1100 px. The existing player-view suite also exercised its 375/700/1100/1440 px cases. Actual browser clicks and Enter opened Full rules and parent Upgrades in the compact build.
- A first journal-suite run shared saved view preferences with the search fixture and found its completed archive already open. With fresh fixture preferences, all eight checks passed. No product change forced archives closed.
- Public HTTP health returned **200 / 1.0.48**, protected-resource metadata returned **200**, and anonymous MCP access correctly returned **401** with an OAuth challenge. Native DnDGPT rule and campaign-list calls succeeded after repair.
- Production deployment: `6addc046a110a23d30c1`.
- Private hosted execution `6addc0cc008e763fe7e4`: **22 hosting/public-connection checks + 15 recovery checks passed**, no real campaign accessed and no model API calls. Gallery file ingestion, durable reopening, image retrieval and unchanged gameplay all passed.

## Limits and use

The hosted file download used a fixture image. It tests file ingestion and real Appwrite persistence; it does not demonstrate ChatGPT handing off the player's three original generated artworks. Only screenshots of those failed attempts were attached here. The originals have not been added to Gallery by this work; retry them from their existing ChatGPT conversation.

Reopen the dashboard to load the new search bar. No ZIP upload or image regeneration is needed for the server update. Player campaigns were not edited.

Local browser reports and preview are in `dndgpt-app/test-results/`. Usage and rebuild instructions: [Dashboard search and Gallery](DASHBOARD_SEARCH_AND_GALLERY.md).
