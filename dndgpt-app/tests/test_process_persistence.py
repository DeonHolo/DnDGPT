"""Loopback-only acceptance of the normal server across real process restarts.

The tiny JWKS fixture issues test tokens directly; it is not an OAuth login
provider. No verifier injection, public tunnel, existing DB or ChatGPT is used.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

from cryptography.hazmat.primitives.asymmetric import rsa
import httpx
import jwt
import pytest

APP = Path(__file__).resolve().parents[1]


class LocalService:
    def __init__(self, folder, issuer):
        self.folder, self.issuer = folder, issuer
        self.database = folder / "sandbox.sqlite3"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        self.process = None
        self.log = None

    def start(self, database=None):
        assert self.process is None
        env = {**os.environ, "DNDGPT_ENV": "test", "DNDGPT_DB": str(database or self.database),
               "DNDGPT_OAUTH_ISSUER": self.issuer.origin,
               "DNDGPT_JWKS_URL": self.issuer.origin + "/jwks",
               "DNDGPT_RESOURCE_URL": self.origin + "/mcp"}
        self.log = (self.folder / "server.log").open("ab")
        self.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.server:app", "--host", "127.0.0.1",
             "--port", str(self.port), "--no-access-log"], cwd=APP, env=env,
            stdin=subprocess.DEVNULL, stdout=self.log, stderr=self.log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            deadline = time.monotonic() + 20
            with httpx.Client(base_url=self.origin, timeout=0.5, trust_env=False) as client:
                while time.monotonic() < deadline:
                    if self.process.poll() is not None:
                        raise AssertionError("Loopback test server exited before readiness")
                    try:
                        if client.get("/api/health").status_code == 200:
                            return
                    except httpx.TransportError:
                        pass
                    time.sleep(0.05)
            raise AssertionError("Loopback test server did not become ready")
        except BaseException:
            self.stop()
            raise

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
            finally:
                self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None

    @contextmanager
    def client(self, token=None):
        headers = {"Authorization": "Bearer " + token} if token else {}
        with httpx.Client(base_url=self.origin, headers=headers,
                          timeout=10, trust_env=False) as client:
            yield client


@pytest.fixture
def process_service(tmp_path):
    class Issuer:
        def __init__(self):
            self.keys = {"first": rsa.generate_private_key(public_exponent=65537, key_size=2048)}
            self.reads = 0

        def token(self, subject="fixture-owner", scopes="campaign:read campaign:write",
                  kid="first", **changes):
            claims = {"iss": self.origin, "aud": service.origin + "/mcp", "sub": subject,
                      "exp": int(time.time()) + 300, "iat": int(time.time()),
                      "scope": scopes, "azp": "shared-test-oauth-client"}
            claims.update(changes)
            return jwt.encode(claims, self.keys[kid], algorithm="RS256", headers={"kid": kid})

    issuer = Issuer()

    class JWKSHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/jwks":
                self.send_error(404)
                return
            issuer.reads += 1
            body = json.dumps({"keys": [
                {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())),
                 "kid": kid, "use": "sig", "alg": "RS256"}
                for kid, key in issuer.keys.items()]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    jwks = ThreadingHTTPServer(("127.0.0.1", 0), JWKSHandler)
    issuer.origin = f"http://127.0.0.1:{jwks.server_port}"
    thread = threading.Thread(target=jwks.serve_forever, daemon=True)
    thread.start()
    service = LocalService(tmp_path, issuer)
    try:
        service.start()
        yield service, issuer
    finally:
        service.stop()
        jwks.shutdown()
        jwks.server_close()
        thread.join(timeout=5)


def rpc(client, method, params=None):
    response = client.post("/mcp", headers={"Accept": "application/json, text/event-stream"},
                           json={"jsonrpc": "2.0", "id": 1, "method": method,
                                 "params": params or {}})
    assert response.status_code == 200
    body = response.json()
    assert "error" not in body
    return body["result"]


def tool(client, name, arguments=None):
    return rpc(client, "tools/call", {"name": name, "arguments": arguments or {}})


def test_real_http_jwks_rotation_and_account_boundaries(process_service):
    service, issuer = process_service
    with service.client() as anonymous:
        for path in ("/api/campaigns", "/mcp"):
            response = anonymous.get(path)
            assert response.status_code == 401
            assert "resource_metadata=" in response.headers["WWW-Authenticate"]
        discovery = anonymous.get("/.well-known/oauth-protected-resource/mcp").json()
        assert discovery["resource"] == service.origin + "/mcp"
        assert discovery["authorization_servers"] == [issuer.origin]
    with service.client(issuer.token()) as owner:
        assert owner.get("/api/campaigns").json() == {"campaigns": []}
        assert issuer.reads > 0  # Normal JwtVerifier fetched a real HTTP JWKS.
        created = tool(owner, "create_sandbox", {"name": "Process fixture", "action_id": "process-create-001"})
        campaign_id = created["structuredContent"]["campaign"]["id"]
        assert not created.get("isError")
    reads = issuer.reads
    issuer.keys["rotated"] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with service.client(issuer.token(kid="rotated", azp="new-registered-client")) as refreshed:
        # PyJWT rate-limits unknown-kid refreshes for 30 seconds after a fetch.
        # Preserve that protection and exercise its real retry path.
        deadline = time.monotonic() + 40
        while True:
            response = refreshed.get("/api/campaigns/" + campaign_id)
            if response.status_code == 200:
                break
            assert response.status_code == 401
            assert time.monotonic() < deadline, "Rotated signing key never became usable"
            time.sleep(0.5)
    assert issuer.reads > reads  # An unfamiliar kid refreshed the JWK set after cooldown.
    for token in (issuer.token(exp=int(time.time()) - 60), issuer.token(iss="https://wrong.invalid"),
                  issuer.token(aud="https://wrong.invalid/mcp"), "malformed.token"):
        with service.client(token) as invalid:
            assert invalid.get("/api/campaigns").status_code == 401
    with service.client(issuer.token(subject="other-owner")) as other:
        assert other.get("/api/campaigns").json() == {"campaigns": []}
        assert other.get("/api/campaigns/" + campaign_id).status_code == 404
        assert tool(other, "get_campaign", {"campaign_id": campaign_id})["isError"]
    with service.client(issuer.token(scopes="campaign:read")) as reader:
        assert reader.get("/api/campaigns/" + campaign_id).status_code == 200
        denied = tool(reader, "create_sandbox", {"name": "Denied", "action_id": "process-denied-001"})
        assert denied["isError"]
        assert "insufficient_scope" in denied["_meta"]["mcp/www_authenticate"][0]


def test_pending_approval_commit_retry_and_backup_survive_process_restarts(process_service):
    service, issuer = process_service
    token = issuer.token()
    preferences = {"panels": ["skills"], "details": ["ability-fixture"], "hud_hidden": False}
    with service.client(token) as owner:
        state = tool(owner, "create_sandbox", {"name": "Restart fixture", "action_id": "restart-create-001"})["structuredContent"]["campaign"]
        campaign_id = state["id"]
        tool(owner, "set_view_preferences", {"preferences": preferences})
        audit_before = tool(owner, "audit", {"campaign_id": campaign_id})["structuredContent"]
        proposal = tool(owner, "propose_action", {"campaign_id": campaign_id,
            "action_id": "restart-resume-001", "expected_version": state["version"],
            "kind": "resume", "payload": {}})
        approval_token = proposal["_meta"]["approval_token"]
        proposal_id = proposal["structuredContent"]["proposal"]["id"]
        assert approval_token not in json.dumps(proposal["structuredContent"])
        assert approval_token not in json.dumps(proposal["content"])
        assert owner.get("/api/campaigns/" + campaign_id).json()["campaign"] == state
        assert tool(owner, "audit", {"campaign_id": campaign_id})["structuredContent"] == audit_before
    service.stop()
    service.start()  # New Python process, same database and normal verifier.
    with service.client(token) as owner:
        view = tool(owner, "render_dashboard", {"campaign_id": campaign_id})
        assert view["structuredContent"]["campaign"] == state
        assert view["structuredContent"]["view_preferences"] == preferences
        assert view["_meta"]["approval"]["approval_token"] == approval_token
        arguments = {"proposal_id": proposal_id, "approval_token": approval_token}
        denied = tool(owner, "execute_confirmed_action", {**arguments, "approval_token": "forged"})
        assert denied["isError"]
        committed = tool(owner, "execute_confirmed_action", arguments)
        assert not committed.get("isError")
        state_after = committed["structuredContent"]["campaign"]
        assert state_after["version"] == state["version"] + 1 and not state_after["paused"]
        audit_after = tool(owner, "audit", {"campaign_id": campaign_id})["structuredContent"]
        assert audit_after["integrity_valid"]
        assert audit_after["event_count"] == audit_before["event_count"] + 1
        backup = service.folder / "backup.sqlite3"
        subprocess.run([sys.executable, "scripts/backup_db.py", str(service.database), str(backup)],
                       cwd=APP, check=True, capture_output=True, timeout=20)
    for database in (service.database, backup):
        service.stop()
        service.start(database)
        with service.client(issuer.token(azp="renewed-client")) as owner:
            retry = tool(owner, "execute_confirmed_action", arguments)
            assert retry["structuredContent"] == committed["structuredContent"]
            # SQLite canonical JSON reorders keys; text content must be semantically equal.
            assert json.loads(retry["content"][0]["text"]) == json.loads(committed["content"][0]["text"])
            assert not retry.get("isError")
            assert owner.get("/api/campaigns/" + campaign_id).json()["campaign"] == state_after
            assert tool(owner, "audit", {"campaign_id": campaign_id})["structuredContent"] == audit_after
            view = tool(owner, "render_dashboard", {"campaign_id": campaign_id})
            assert view["structuredContent"]["view_preferences"] == preferences
            assert view["_meta"]["approval"] is None
