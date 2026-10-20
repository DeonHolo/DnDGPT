import copy

import pytest

from scripts.evaluate_generation import evaluate, SCENARIOS


def sample():
    # Synthetic harness test only; never used as published generation evidence.
    corpus = {"provenance": "saved_generated_output", "abilities": [{"id": "test", "name": "Test only",
              "utility": True, "text": "Inspect an accessible ordinary material."}]}
    review = {"reviewer": "Harness test", "kits": [], "abilities": [{"id": "test", "role": "Analysis",
        "clarity": "Partial", "finding": "Needs a resolution rule", "evidence": "accessible ordinary material",
        "scenarios": {key: {"verdict": "conditional", "reason": "Only if material is accessible"} for key in SCENARIOS}}]}
    return corpus, review


def test_review_counts_coverage_without_inventing_a_quality_score():
    corpus, review = sample()
    result = evaluate(corpus, review)
    assert result["sampled_abilities"] == 1 and result["utility_scenario_judgments"] == 4
    assert "score" not in result and result["campaign_writes"] == result["model_calls"] == 0


@pytest.mark.parametrize("mutation", [lambda c, r: c.update(provenance="synthetic_fixture"),
    lambda c, r: r["abilities"][0].update(evidence="An invented rule"),
    lambda c, r: r["abilities"][0]["scenarios"].pop("travel"),
    lambda c, r: r["abilities"].append(copy.deepcopy(r["abilities"][0]))])
def test_review_rejects_synthetic_provenance_invented_evidence_and_missing_coverage(mutation):
    corpus, review = sample()
    mutation(corpus, review)
    with pytest.raises(ValueError):
        evaluate(corpus, review)
