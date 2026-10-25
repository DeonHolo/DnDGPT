# Dashboard search and Gallery connection

The search bar below Saved game searches the selected campaign. Enter part of a name or several words, then choose a result to open its chapter, subtab and matching entry. Enter opens the first result; arrow keys move through results; Escape closes the list.

Skills open Full rules. A dependent upgrade opens its parent ability's Upgrades tab. Equipment details, completed quest archives and older campaign-log entries open automatically. Search includes character/story text, health, allies, public world entries and Sovereignty records. Gallery labels become searchable after opening Gallery. Switching campaigns or games clears the search.

Filtering and showing more results happen in the browser. Typing makes no server or model requests. Search uses player-facing fields from the current dashboard snapshot; it does not search other campaigns or GM-only records.

Maintainers: after editing a dashboard module, run `python -m scripts.build_dashboard_scripts` from `dndgpt-app` and commit `app/dashboard_modules.min.js`. The hosted service needs no Node/npm dependency. CI checks the source hash and the dashboard's existing 1 MB resource limit.

## Gallery outage on 2026-10-25

The public connection returned `503 storage_unavailable` even for health checks and campaign/rule reads. Safe provider diagnostics identified `401 api_key_invalid` from its injected storage credential. Internal Appwrite executions of the same code succeeded, so those earlier checks did not cover the failure.

Release 1.0.47 restored public access using a dedicated secret storage credential with `tables.read`, `rows.read`, `rows.write`. Existing OAuth and campaign ownership checks still apply. The art-generation prompt and generated-image file schema did not cause this outage. The file schema matches [OpenAI's file-input contract](https://developers.openai.com/plugins/reference#define-file-inputs).

Release 1.0.48 adds search and expands the private hosted probe with Gallery file ingestion/reopening/gameplay-isolation checks and public HTTP health/version, OAuth metadata and anonymous-denial checks. Its image download is a fixture; these checks do not demonstrate ChatGPT handing off the player's three original generated images. Those images must be retried from the conversation that contains them.
