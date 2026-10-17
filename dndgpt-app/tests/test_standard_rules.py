import copy

import pytest

from app.chat_game import ChatGame, apply_changes, apply_lifecycle
from app.engine import EngineError
from app.standard_rules import PROFILE, ability_kind, class_kit_check


def kit(utilities):
    rows = [{"id": kind, "source": "class", "activation": kind}
            for kind in ("Action", "Passive", "Reaction", "Free Action")]
    return rows + [{"id": f"utility-{i}", "source": "class", "activation": "Passive—utility"}
                   for i in range(utilities)]


def test_new_chat_uses_current_resource_contract_and_attribute_allocation(engine):
    state = ChatGame(engine).create("owner-a", "Resource test", "resources-create", True)
    c = state["character"]
    assert (c["hp"], c["hp_max"], c["mp"], c["mp_max"]) == (60, 60, 100, 100)
    assert "sta" not in c and "sta_max" not in c
    state = apply_changes(state, {"character": {"attributes": {"INT": 9, "STR": 7}}})
    assert (state["character"]["hp_max"], state["character"]["mp_max"]) == (66, 120)
    with pytest.raises(EngineError) as error:
        apply_changes(state, {"character": {"sta": 60}})
    assert error.value.code == "unsupported_resource"


@pytest.mark.parametrize("rarity,minimum", [("EPIC", 1), ("LEGENDARY", 1), ("UNIQUE", 2)])
def test_standard_confirmation_requires_full_class_kit(engine, rarity, minimum):
    state = ChatGame(engine).create("owner-a", "Kit test", "kit-create", True)
    state["character"].update(class_name="Test class", rarity=rarity)
    state["abilities"] = kit(minimum - 1)
    # A Signature Utility does not pay for a class-native guarantee.
    state["abilities"].append({"id": "signature-utility", "source": "signature",
                                "group": "utility", "activation": "Passive"})
    assert class_kit_check(state)["missing"] == ["1 utility"]
    with pytest.raises(EngineError) as error:
        apply_lifecycle(state, "confirm_chat_character", {})
    assert error.value.code == "incomplete_class_kit"
    assert state["phase"] == "character_draft"
    state["abilities"] = kit(minimum)
    apply_lifecycle(state, "confirm_chat_character", {})
    assert state["phase"] == "ready" and state["paused"]


@pytest.mark.parametrize("activation,group", [("Passive—utility", None), ("Passive", "Utility"),
                                            ("Action", "Exploration & Utility")])
def test_utility_role_has_priority_over_activation(activation, group):
    assert ability_kind({"activation": activation, "group": group}) == "utility"


def test_legacy_and_custom_characters_keep_their_recorded_rules(engine):
    state = ChatGame(engine).create("owner-a", "Legacy test", "legacy-profile-create", True)
    state.pop("rules_profile")
    state["character"].update(class_name="Legacy class", rarity="UNIQUE", hp=95, hp_max=95,
                              sta=60, sta_max=60)
    before = copy.deepcopy(state)
    updated = apply_changes(state, {"notes": "Read without migration"})
    assert updated["character"] == before["character"]
    apply_lifecycle(updated, "confirm_chat_character", {})
    custom = copy.deepcopy(before)
    custom["rules_profile"] = PROFILE
    custom["creation"]["rules_source"] = "custom"
    assert class_kit_check(custom)["missing"] == []
    apply_lifecycle(custom, "confirm_chat_character", {})
    assert custom["phase"] == "ready"


def test_scene_preferences_round_trip_without_changing_campaign(engine):
    state = ChatGame(engine).create("owner-a", "Scene test", "scene-create", True)
    preferences = {"panels": ["skills"], "details": [], "hud_hidden": False, "scene": "moonkeep"}
    engine.set_view_preferences("owner-a", preferences)
    assert engine.get_view_preferences("owner-a") == preferences
    assert engine.get_campaign("owner-a", state["id"])["character"] == state["character"]
    with pytest.raises(EngineError):
        engine.set_view_preferences("owner-a", {**preferences, "scene": "not-a-theme"})
