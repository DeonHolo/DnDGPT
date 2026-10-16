import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import AuthConfig, JwtVerifier, owner_id
from app.engine import Engine
from app.server import create_app
from app.storage import Store


@pytest.fixture(scope="session")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def config():
    return AuthConfig("https://issuer.example.test", "https://issuer.example.test/jwks",
                      "https://dndgpt.example.test/mcp")


@pytest.fixture
def tokens(signing_key, config):
    def issue(subject="user-a", scopes="campaign:read campaign:write", **changes):
        claims = {"iss": config.issuer, "aud": config.resource_url, "sub": subject,
                  "exp": int(time.time()) + 300, "iat": int(time.time()),
                  "scope": scopes, "azp": "same-oauth-client-for-every-user"}
        claims.update(changes)
        return jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": "test-key"})
    return issue


@pytest.fixture
def verifier(signing_key, config):
    # Test-only in-process JWKS equivalent; real signatures/claims are verified.
    return JwtVerifier(config, key_provider=lambda _: signing_key.public_key())


@pytest.fixture
def web(tmp_path, config, verifier, tokens):
    app = create_app(tmp_path / "web.sqlite3", config, verifier)
    with TestClient(app, base_url="https://dndgpt.example.test",
                    headers={"Authorization": "Bearer " + tokens()}) as client:
        yield client


@pytest.fixture
def engine(tmp_path):
    store = Store(tmp_path / "engine.sqlite3")
    store.initialize()
    return Engine(store)


@pytest.fixture
def state(engine):
    return engine.create_sandbox("owner-a", "Test Solo", "create-action-001")


def commit(engine, state, kind, payload=None, action_id=None, owner="owner-a"):
    action_id = action_id or f"test-action-{state['version']:05d}"
    proposal = engine.propose_action(owner, state["id"], action_id, state["version"], kind, payload or {})
    return engine.execute_confirmed_action(owner, proposal["proposal"]["id"],
                                           proposal["_meta"]["approval_token"])
