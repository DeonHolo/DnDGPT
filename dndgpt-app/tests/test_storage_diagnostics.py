import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app.appwrite_entry import main
from app.appwrite_store import AppwriteAPI
from app.engine import EngineError


@pytest.mark.parametrize("status,kind", [(401, "user_unauthorized"), (403, "general_unauthorized_scope"),
                                        (429, "general_rate_limit_exceeded")])
def test_storage_diagnostics_keep_status_and_type_without_credentials(status, kind):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(status,
            json={"type": kind, "message": "PRIVATE_PROVIDER_MESSAGE"}))) as client:
        api = AppwriteAPI("https://fixture.example.test/v1", "fixture-project", "PRIVATE_KEY", client=client)
        with pytest.raises(EngineError) as rejected:
            api.call("GET", "/tablesdb/fixture/tables/records")
        error = rejected.value
        assert error.code == "storage_unavailable" and error.status == 503
        assert error.upstream_status == status and error.upstream_type == kind
        assert "PRIVATE" not in str(error)


def test_entry_logs_only_sanitized_storage_diagnostics(monkeypatch):
    import app.appwrite_entry as entry
    monkeypatch.setenv("APPWRITE_FUNCTION_API_ENDPOINT", "https://fixture.example.test/v1")
    monkeypatch.setenv("APPWRITE_FUNCTION_PROJECT_ID", "fixture-project")
    error = EngineError(503, "storage_unavailable", "Hosted storage rejected the request")
    error.upstream_status, error.upstream_type = 401, "user_unauthorized"
    def reject(*args, **kwargs):
        raise error
    monkeypatch.setattr(entry, "AppwriteAPI", reject)
    messages = []
    context = SimpleNamespace(req=SimpleNamespace(headers={"x-appwrite-key": "PRIVATE_KEY"}),
                              error=messages.append, res=SimpleNamespace(json=lambda body, status: (body, status)))
    body, status = asyncio.run(main(context))
    assert status == 503 and "upstream" not in str(body)
    assert messages == ["Hosted storage rejected request: status=401 type=user_unauthorized"]


@pytest.mark.parametrize("configured", [False, True])
def test_storage_credential_comes_from_hosted_secret_or_execution(monkeypatch, configured):
    import app.appwrite_entry as entry
    monkeypatch.setenv("APPWRITE_FUNCTION_API_ENDPOINT", "https://fixture.example.test/v1")
    monkeypatch.setenv("APPWRITE_FUNCTION_PROJECT_ID", "fixture-project")
    monkeypatch.delenv("DNDGPT_APPWRITE_STORAGE_KEY", raising=False)
    if configured:
        monkeypatch.setenv("DNDGPT_APPWRITE_STORAGE_KEY", "HOSTED_PRIVATE_KEY")
    seen = []
    def capture(endpoint, project, key, **kwargs):
        seen.append(key)
        raise EngineError(503, "fixture_stop", "Fixture stopped before storage")
    monkeypatch.setattr(entry, "AppwriteAPI", capture)
    context = SimpleNamespace(req=SimpleNamespace(headers={"x-appwrite-key": "EXECUTION_KEY",
        "DNDGPT_APPWRITE_STORAGE_KEY": "UNTRUSTED_HEADER"}),
        res=SimpleNamespace(json=lambda body, status: (body, status)))
    body, status = asyncio.run(main(context))
    assert seen == ["HOSTED_PRIVATE_KEY" if configured else "EXECUTION_KEY"]
    assert status == 503 and "KEY" not in str(body)


@pytest.mark.parametrize("health_status", [200, 503])
def test_public_probe_catches_failure_that_internal_execution_can_miss(health_status):
    from app.version import APP_VERSION
    from appwrite_probe import check_public_connection
    resource = "https://fixture.example.test/mcp"
    def respond(request):
        if request.url.path == "/api/health":
            return httpx.Response(health_status, json={"version": APP_VERSION})
        if request.method == "POST":
            return httpx.Response(401, headers={"www-authenticate": 'Bearer resource_metadata="fixture"'})
        return httpx.Response(200, json={"resource": resource})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        if health_status == 503:
            with pytest.raises(AssertionError):
                check_public_connection(client, resource)
        else:
            assert len(check_public_connection(client, resource)) == 3
