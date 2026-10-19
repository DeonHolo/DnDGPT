# Hosting and deployment

Maintainer notes for the hosted DnDGPT service. Players should use [Start playing](../README.md#start-playing).

The Python Function serves the backend and the MCP App dashboard resource. A separate website is optional. See the [Appwrite deployment guide](../dndgpt-app/APPWRITE_HOSTING.md) and [authentication setup](../dndgpt-app/AUTH0_SETUP.md).

**Deployment flow:** develop locally → run relevant tests → push to `main` → Appwrite builds changes under `dndgpt-app/**` → the stable domain serves the new deployment.

GitHub Actions now runs the test suite and checks document synchronization on pushes to `main` and pull requests. After checks pass, it builds a portable plugin ZIP as a downloadable run artifact. The ZIP includes the current rulebook, hardener, instructions, art and licenses, uses the stable hosted MCP endpoint, and contains no personal App binding or credentials. Appwrite's Git integration deploys independently; the GitHub check does not currently gate that webhook. Use a passing checked revision for releases.

Backend/dashboard changes keep the same server address. ChatGPT can retain older dashboard HTML: close the old dashboard, refresh the connection's tools if needed, reload ChatGPT, and ask for a new `render_dashboard` call for the existing campaign.

## Where the rules live

The authoritative editable documents are `dndgpt-app/rules/rulebook-v1.0.txt` and `dndgpt-app/rules/rule-hardener.txt`. Appwrite deploys those files. The authenticated `read_rules` tool serves full documents, a source-derived index (`document=index`), or exact rulebook sections (`section=KEY`) in pages with the canonical document hash. The GM loads the compact hardener and index, then retrieves all applicable chapters/amendments before deciding. Offsets are relative to the requested selection; a completed section is not a complete manual read. Failed or partial reads must never be reported as complete. Full-document access remains available for audits and offline fallback.

The plugin also contains copies under `skills/game-master/references/`. They make the package self-contained and provide a fallback when the hosted tools are unavailable. Existing custom-rule campaigns keep their explicitly chosen rules. Merely changing either document does not migrate saved characters, spend resources, replace published offers or advance play.

After an audited rules amendment, run from `dndgpt-app`:

```sh
python -m scripts.sync_plugin_rules
python -m pytest tests/test_sources.py tests/test_plugin_package.py -q
```

The synchronization command copies bytes from backend source to the plugin; it does not rewrite rule integrity history. Record the amendment and update `rules/integrity.json` through the revision process. CI and the package builder reject mismatched copies instead of shipping a stale fallback.

## Two release steps

1. Push the tested revision to `main` and verify Appwrite's deployment and hosted document hashes.
2. For bundled rule, skill, metadata or icon changes, bump the package version and update the existing plugin through Plugin Creator's authenticated `update_plugin` workflow, preserving its identity and App binding. Read back the uploaded files. The CI portable ZIP is an alternative upload input for a separate portable/public integration; do not replace an existing personal App binding casually.

The current private plugin is not Git-synced. An Appwrite deployment does not publish its ZIP. [OpenAI's publishing documentation](https://developers.openai.com/plugins/deploy/submission) separates automatic hosted-MCP checks from metadata/skill ZIP updates. The available Plugin Creator tool can publish an authorized account update from this session; it is not a GitHub Actions action or a supported publishing credential for CI. No documented external CI publication API was established during this review. Do not export a ChatGPT session token into GitHub secrets to imitate one.

An extra static Appwrite API key is unnecessary for this flow. Appwrite MCP is already authenticated, Git deployment uses the installed GitHub integration, and the Function receives scoped runtime database access through `x-appwrite-key`. An Appwrite key cannot publish ChatGPT plugin metadata or skills.

**Current status:** cloud-hosted private beta. Real Appwrite fixture checks and the creator's ChatGPT sign-in, save, display and reopen flow have passed. Independent-player installation and public-directory publication remain separate acceptance steps.

For the public integration packaging instructions, see [Package your own ChatGPT integration](../README.md#package-your-own-chatgpt-integration).
