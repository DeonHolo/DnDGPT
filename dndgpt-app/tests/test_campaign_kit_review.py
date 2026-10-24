import copy

import pytest

from scripts.evaluate_campaign_kits import evaluate, SCENARIOS, UTILITY_CASES


def sample():
    # Harness-only fixture, never included in the actual generation report.
    case = {"verdict": "conditional", "reason": "Requires an accessible material", "evidence": "shape accessible material"}
    kits = [{"id": game, "game_id": game, "text": "Can shape accessible material. Evolution can move the material.",
             "abilities": [{"scope": "sovereign", "sovereign_role": role, "activation": "Passive"} for role in ("domain", "general", "army")],
             "utilities": [{"id": str(i), "text": "shape accessible material"} for i in range(2)]}
            for game in ("age-of-convergence", "sovereign-system")]
    rows = [{"id": k["id"], "scenarios": {s: copy.deepcopy(case) for s in SCENARIOS},
             "utilities": {str(i): {s: copy.deepcopy(case) for s in UTILITY_CASES} for i in range(2)},
             **{key: {"finding": "A recorded harness judgment", "evidence": "shape accessible material"} for key in
                ("class_identity", "redundancy", "evolution_difference")}} for k in kits]
    return {"provenance": "development_generated_output", "generated_by": "Harness label", "kits": kits}, {"reviewer": "Harness label", "kits": rows}


def test_review_checks_both_games_and_all_situations():
    c, r = sample()
    result = evaluate(c, r)
    assert result["scenario_judgments"] == 26 and not result["findings"]
    assert result["model_calls_during_gameplay"] == 0 and "score" not in result


def test_missing_sovereign_kit_and_supported_generation_defects_block_an_offer():
    c, r = sample(); c["kits"][1]["abilities"] = []
    r["kits"][0]["findings"] = [{"finding": "Known defect in this harness case", "evidence": "shape accessible material"}]
    result = evaluate(c,r)
    assert len(result["findings"]) == 2 and not result["ready_for_offer"]


@pytest.mark.parametrize("edit", [lambda c,r: c.update(provenance="synthetic_fixture"),
    lambda c,r: c["kits"].pop(), lambda c,r: r["kits"][0]["scenarios"].pop("escape"),
    lambda c,r: r["kits"][0]["scenarios"]["combat"].update(evidence="An invented rule"),
    lambda c,r: r["kits"][0].pop("evolution_difference")])
def test_review_rejects_invented_evidence_and_missing_coverage(edit):
    c, r = sample(); edit(c,r)
    with pytest.raises(ValueError):
        evaluate(c,r)
