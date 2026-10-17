import pytest

from app import records
from app.campaign_lifecycle import CampaignLifecycle
from app.engine import EngineError


def test_campaign_delete_is_previewed_owner_scoped_and_resumable(engine, state):
    other = engine.create_sandbox("owner-a", "Keep this campaign", "keep-campaign-001")
    lifecycle = CampaignLifecycle(engine)

    with pytest.raises(EngineError) as cross_owner:
        lifecycle.preview_delete("owner-b", state["id"], state["version"])
    assert cross_owner.value.status == 404

    with engine.store.transaction() as db:
        for number in range(2, 31):
            records.insert(db, "events_v1", {
                "campaign_id": state["id"], "number": number, "event": "{}",
                "previous_hash": "", "hash": ""
            })

    preview = lifecycle.preview_delete("owner-a", state["id"], state["version"])
    assert preview["campaign_name"] == "Test Solo"
    assert preview["deleted"] is False
    assert engine.get_campaign("owner-a", state["id"]) == state

    with pytest.raises(EngineError) as unconfirmed:
        lifecycle.delete("owner-a", state["id"], state["version"],
                         preview["confirmation_token"], False)
    assert unconfirmed.value.code == "confirmation_required"

    first = lifecycle.delete("owner-a", state["id"], state["version"],
                             preview["confirmation_token"], True)
    assert first["cleanup_pending"] is True
    assert first["removed_records"]["events_v1"] == 20
    assert [item["id"] for item in engine.list_campaigns("owner-a")] == [other["id"]]

    final = lifecycle.delete("owner-a", state["id"], state["version"],
                             preview["confirmation_token"], True)
    assert final["deleted"] is True
    assert final["removed_records"]["events_v1"] == 30
    assert engine.get_campaign("owner-a", other["id"]) == other
    with engine.store.transaction() as db:
        assert records.find(db, "events_v1", {"campaign_id": state["id"]}) == []

    with pytest.raises(EngineError) as deleted:
        engine.get_campaign("owner-a", state["id"])
    assert deleted.value.code == "campaign_deleted"
    with pytest.raises(EngineError) as stale_create:
        engine.create_sandbox("owner-a", "Test Solo", "create-action-001")
    assert stale_create.value.code == "campaign_deleted"
