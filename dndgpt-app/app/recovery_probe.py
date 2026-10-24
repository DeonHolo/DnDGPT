"""Disposable recovery/overhead experiment, shared by local and private hosted probes."""
import copy
import time

from .campaign_archive import CampaignArchive
from .chat_game import ChatGame
from .continuity import model_view
from .engine import Engine, EngineError
from .save_history import SaveHistory
from .storage import canonical


def check_recovery(engine, owner, state, run):
    """Call only with a probe-owned disposable campaign. Never advances its fiction."""
    assert state["disposable"] and state["mode"] == "chat"
    game = ChatGame(engine)
    timings, checks, api_calls = {}, [], []
    api = getattr(engine.store, "api", None)
    original_call = api.call if api else None
    if api:
        def counted(method, path, **kwargs):
            api_calls.append(method + " " + path.split("?")[0])
            return original_call(method, path, **kwargs)
        api.call = counted

    def measure(name, operation):
        start, count = time.perf_counter(), len(api_calls)
        result = operation()
        timings[name] = {"seconds": round(time.perf_counter() - start, 4),
                         "storage_api_calls": len(api_calls) - count if api else None}
        return result

    try:
        changes = {"continuity": {"scene": "Disposable recovery scene", "last_player_intent": "Inspect the fixture",
            "last_action": "Inspected the fixture", "outcome": "The fixture is intact",
            "pending_decision": "Continue the test?", "unresolved_threads": ["Fixture repair pending"],
            "npc_commitments": ["Fixture keeper returns at noon"]},
            "world": {"summary": "Disposable overhead fixture", "article": "Recorded setting detail. " * 400},
            "upsert": {"world_log": [{"id": "probe-log-" + str(i), "text": "Recorded past event. " * 40} for i in range(60)]}}
        changes["upsert"]["world_log"][0].update(
            text="The fixture keeper promises to return at noon and sees the repaired landing reopen.", witnesses=["fixture-keeper"])
        changes["life_updates"] = {
            "actors": [{"id": "fixture-keeper", "name": "Fixture keeper", "kind": "npc", "description": "Disposable test character."}],
            "places": [{"id": "fixture-landing", "name": "Fixture landing", "kind": "location", "description": "A disposable crossing."}],
            "events": [{"id": "fixture-promise", "kind": "commitment", "subject_id": "fixture-keeper",
                        "source_id": "probe-log-0", "commitment_id": "return-noon", "status": "open",
                        "summary": "The fixture keeper returns at noon."},
                       {"id": "fixture-reopening", "kind": "place_change", "subject_id": "fixture-landing",
                        "source_id": "probe-log-0", "summary": "The repaired landing reopens.",
                        "feature": {"id": "passage", "name": "Working crossing", "description": "Passage is available."}}]}
        updated = measure("batched_save", lambda: game.update(owner, state["id"], "continuity-" + run,
            state["version"], "Disposable continuity and size fixture", changes))["campaign"]
        assert updated["fictional_time_seconds"] == state["fictional_time_seconds"]
        assert updated["character"] == state["character"] and updated["paused"] == state["paused"]
        checks.append("continuity_in_existing_save")
        assert updated["campaign_life"]["actors"][0]["commitments"][0]["text"] == "The fixture keeper returns at noon."
        assert updated["campaign_life"]["places"][0]["features"][0]["id"] == "passage"
        checks.append("living_memory_in_existing_save")
        measure("separate_state_and_approval_reads", lambda: (
            engine.get_campaign(owner, updated["id"]), engine.pending_approval(owner, updated["id"])))
        context = measure("combined_state_and_approval_read", lambda: engine.campaign_context(owner, updated["id"]))
        assert context["campaign"] == updated and context["campaign"]["resume_brief"]["read_only"]
        checks.append("read_only_resume")
        sizes = {view: len(canonical(model_view(updated, view)).encode()) for view in ("full", "turn", "resume")}
        assert sizes["resume"] < sizes["turn"] < sizes["full"]
        assert model_view(updated, "turn")["abilities"] == updated["abilities"]
        checks.append("compact_response_preserves_mechanics")
        updated = measure("world_excerpt_save", lambda: game.update(owner, updated["id"],
            "world-merge-" + run, updated["version"], "Preserve omitted world detail",
            {"world": model_view(updated, "turn")["world"]}))["campaign"]
        assert updated["world"]["article"] == changes["world"]["article"]
        checks.append("compact_world_update_preserves_details")
        full = measure("full_history_read", lambda: engine.get_campaign(owner, updated["id"]))
        assert full == updated and len(full["world_log"]) == 60
        assert full["world_log"][0]["id"] == "probe-log-0"
        assert len(model_view(full, "turn")["world_log"]) == 3
        checks.append("full_read_recovers_omitted_history")
        history = SaveHistory(engine)
        page = measure("history_page", lambda: history.list(owner, updated["id"], limit=1))
        assert page["next_before"] and page["versions"][0]["version"] == updated["version"]
        assert history.compare(owner, updated["id"], updated["version"])["historical"]
        checks.append("paged_read_only_history")
        archive = CampaignArchive(engine)
        exported = measure("export", lambda: archive.export(owner, updated["id"]))["archive"]
        assert archive.preview(exported)["overwrites_existing"] is False
        assert engine.get_campaign(owner, updated["id"]) == updated
        damaged = copy.deepcopy(exported)
        damaged["campaign"]["name"] = "Corrupted fixture"
        try:
            archive.preview(damaged)
            raise AssertionError("Corrupted archive accepted")
        except EngineError as error:
            assert error.code == "archive_checksum"
        checks.append("corrupt_archive_rejected")
        restored_result = measure("restore_paused_copy", lambda: archive.restore(owner, exported, "restore-" + run, True))
        restored = restored_result["campaign"]
        assert restored["id"] != updated["id"] and restored["paused"]
        assert restored["character"] == updated["character"] and restored["continuity"] == updated["continuity"]
        assert restored["campaign_life"] == updated["campaign_life"]
        checks.append("living_memory_restored")
        assert restored["phase"] == updated["phase"] and restored["fictional_time_seconds"] == updated["fictional_time_seconds"]
        assert archive.restore(owner, exported, "restore-" + run, True) == restored_result
        assert engine.get_campaign(owner, updated["id"]) == updated
        reopened = Engine(type(engine.store)(engine.store.api)) if api else engine
        assert reopened.get_campaign(owner, restored["id"]) == restored
        assert reopened.audit(owner, restored["id"])["integrity_valid"]
        checks += ["portable_paused_restore", "restore_exact_retry", "source_preserved", "restored_fresh_instance_reopen"]
        return {"checks": checks, "timings": timings, "model_campaign_bytes": sizes,
                "measurement_scope": "Disposable mature-history fixture; model-visible campaign JSON and storage only. The widget still receives its full snapshot in hidden metadata. No model generation timing."}
    finally:
        if api:
            api.call = original_call
