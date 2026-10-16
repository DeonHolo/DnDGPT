"""OAuth resource-server authentication. Login and PKCE are provided by an IdP."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import anyio
import jwt
from mcp.server.auth.provider import AccessToken

READ_SCOPE = "campaign:read"
WRITE_SCOPE = "campaign:write"


@dataclass(frozen=True)
class AuthConfig:
    issuer: str | None = None
    jwks_url: str | None = None
    resource_url: str = "http://127.0.0.1:8765/mcp"
    production: bool = False

    @property
    def configured(self):
        return bool(self.issuer and self.jwks_url)

    def validate(self):
        if bool(self.issuer) != bool(self.jwks_url):
            raise ValueError("Configure both DNDGPT_OAUTH_ISSUER and DNDGPT_JWKS_URL")
        for value in (self.issuer, self.jwks_url, self.resource_url):
            if value is None:
                continue
            parsed = urlsplit(value)
            local = parsed.hostname in ("127.0.0.1", "localhost", "::1")
            if (not parsed.hostname or parsed.username or parsed.password or parsed.query
                    or parsed.fragment or parsed.scheme != "https" and not
                    (local and parsed.scheme == "http" and not self.production)):
                raise ValueError("OAuth URLs must use HTTPS; local development may use loopback HTTP")
        if not self.resource_url.endswith("/mcp"):
            raise ValueError("DNDGPT_RESOURCE_URL must end with /mcp")
        if self.production and not self.configured:
            raise ValueError("Production requires configured OAuth issuer and JWKS")

    @classmethod
    def from_env(cls):
        return cls(os.getenv("DNDGPT_OAUTH_ISSUER"), os.getenv("DNDGPT_JWKS_URL"),
                   os.getenv("DNDGPT_RESOURCE_URL", "http://127.0.0.1:8765/mcp"),
                   os.getenv("DNDGPT_ENV") == "production")


class JwtVerifier:
    def __init__(self, config: AuthConfig, key_provider=None):
        self.config = config
        self.key_provider = key_provider
        self.jwks = jwt.PyJWKClient(config.jwks_url, cache_jwk_set=True, lifespan=300,
                                   timeout=5) if config.jwks_url and not key_provider else None

    def _verify(self, token):
        if not self.config.configured:
            return None
        try:
            key = (self.key_provider(token) if self.key_provider else
                   self.jwks.get_signing_key_from_jwt(token).key)
            claims = jwt.decode(token, key, algorithms=["RS256", "ES256", "EdDSA"],
                                issuer=self.config.issuer, audience=self.config.resource_url,
                                options={"require": ["exp", "iss", "aud", "sub"]})
            subject = claims["sub"]
            if not isinstance(subject, str) or not subject.strip():
                return None
            scopes = claims.get("scope", claims.get("scp", []))
            scopes = scopes.split() if isinstance(scopes, str) else scopes
            if not isinstance(scopes, list) or any(not isinstance(s, str) for s in scopes):
                return None
            return AccessToken(token=token, client_id=str(claims.get("azp", "oauth-client")),
                               subject=subject, scopes=scopes, expires_at=int(claims["exp"]),
                               resource=self.config.resource_url, claims=claims)
        except (jwt.PyJWTError, ValueError, TypeError, OSError):
            return None

    async def verify_token(self, token):
        return await anyio.to_thread.run_sync(self._verify, token)


def owner_id(token: AccessToken):
    """Ownership follows issuer + subject, never OAuth client ID or user input."""
    claims = token.claims or {}
    issuer, subject = claims.get("iss"), token.subject
    if not isinstance(issuer, str) or not issuer or not isinstance(subject, str) or not subject:
        raise PermissionError("Verified subject and issuer required")
    return hashlib.sha256((issuer + "\0" + subject).encode()).hexdigest()
