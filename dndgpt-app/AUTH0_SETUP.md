# OAuth setup

The service verifies signed access tokens, issuer, expiry, resource audience and required scopes. Auth0 is one supported provider; the source contains no configured tenant or account credentials.

Configure a provider API/resource with the **exact** public MCP URL as its audience. Define `campaign:read` and `campaign:write`. For a compatible ChatGPT connection use an authorization-code client with PKCE, the callback URL shown by the client, and refresh access only if needed. Grant that client the explicit scopes; do not enable anonymous or global API access.

Set these environment variables before starting the service:

```text
DNDGPT_ENV=production
DNDGPT_DB=/persistent-storage/campaigns.sqlite3
DNDGPT_OAUTH_ISSUER=https://your-issuer.example/
DNDGPT_JWKS_URL=https://your-issuer.example/.well-known/jwks.json
DNDGPT_RESOURCE_URL=https://your-server.example/mcp
```

Use your provider's actual issuer and JWKS URL, not the placeholders. The API resource, issued-token audience, service resource URL and ChatGPT connection must agree. A stable address avoids changing this configuration after each tunnel restart.

Verify public `/api/health`, protected `/.well-known/oauth-protected-resource`, rejection of anonymous `/mcp`, real sign-in and a disposable end-to-end save. Never publish access/refresh tokens, tunnel tokens, client secrets or campaign data. The local fixture host is for tests only and must not serve as public authentication.
