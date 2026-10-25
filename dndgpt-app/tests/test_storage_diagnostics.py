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
