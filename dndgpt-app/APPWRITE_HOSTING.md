# Appwrite hosting

The Python service runs as an **Appwrite Function**. The existing HTML/JavaScript dashboard is delivered as an MCP App resource inside ChatGPT; a separate Appwrite Site is optional.

GitHub supplies source and automatic builds. Connecting a repository does not convert a local SQLite file into a persistent cloud database.

## Deployment configuration

- Repository root directory: `dndgpt-app`
- Runtime: Python 3.14
- Entrypoint: `appwrite_main.py`
- Keep the imported `main` asynchronous: Appwrite already runs an event loop; await the ASGI dispatch instead of nesting `asyncio.run()`.
- Python request fields use `body_binary` and `query_string`; JavaScript examples use different field names.
- Build command: `pip install -r requirements-hosted.txt`
- Runtime scopes: `tables.read`, `rows.read`, `rows.write`
- Public HTTP invocation reaches the application's existing OAuth checks. Game data requires a valid issuer, audience, subject and scopes.
- Keep database/table permissions empty and row security enabled. Functions use their per-execution server credential; players do not receive that credential.

Environment variables:

```text
DNDGPT_ENV=production
DNDGPT_APPWRITE_DATABASE=dndgpt
DNDGPT_APPWRITE_TABLE=records
DNDGPT_RESOURCE_URL=https://YOUR-FUNCTION-DOMAIN/mcp
DNDGPT_OAUTH_ISSUER=https://YOUR-ISSUER/
DNDGPT_JWKS_URL=https://YOUR-ISSUER/.well-known/jwks.json
```

Appwrite supplies `APPWRITE_FUNCTION_API_ENDPOINT`, `APPWRITE_FUNCTION_PROJECT_ID` and the `x-appwrite-key` execution header. No permanent Appwrite API key belongs in the repository.

Set environment variables before deployment, or redeploy after changing them. A domain tied to a VCS branch follows that branch's deployments; activating a separate commit deployment does not retarget the branch domain. Verify the domain's actual deployment ID and HTTP response after rollout.

`app/records.py` keeps persistence calls separate from game rules. SQLite remains the default local backend. `app/appwrite_store.py` stores current records, immutable versions, audit events, approvals and roll receipts in TablesDB transactions. It never persists a database file in a function container. The optional legacy creation-draft adapter is disabled on this backend.

Existing-row reads stage a private guard update and use the returned snapshot before checking a version; business writes commit atomically. Read-only operations roll back their staged guards. Concurrent conflicts return an error; clients retry the same action ID to recover an existing committed receipt.

## Acceptance

1. Run the Python regression suite and hosted contract tests.
2. Run `appwrite_probe.py` in a **private function with no public execution permissions** against disposable fixture records.
3. Verify `/api/hosting-readiness`, protected-resource metadata, anonymous denial and signed HTTP/MCP requests on the public function.
4. Verify sign-in, save, display and reopening in regular ChatGPT and with a separate real account before claiming player sharing.

The private probe is not the public entrypoint. Never import an existing campaign merely to test hosting. Normal narration continues in ChatGPT; no inference API is added.

Public directory distribution additionally requires OpenAI's submission/review/publishing process. Hosting by itself does not publish the plugin.

Sources: [Appwrite Functions](https://appwrite.io/docs/products/functions), [transactions](https://appwrite.io/docs/products/databases/tablesdb/transactions), [OpenAI plugin publishing](https://developers.openai.com/plugins/deploy/submission).
