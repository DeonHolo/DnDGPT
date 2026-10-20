"""Validate an evidence-based human review of actual outputs. No model calls or gameplay writes.

python -m scripts.evaluate_generation --corpus test-results/generated-corpus.json
    --review test-results/generated-review.json --output test-results/generated-quality.json
Coverage is measured; creativity, balance and usefulness require recorded judgments.
"""
import argparse
import json
from pathlib import Path

SCENARIOS = ("travel", "shelter_and_repairs", "information", "helping_people")
VERDICTS = {"supported", "conditional", "unsupported", "unclear"}


def evaluate(corpus, review):
    if corpus.get("provenance") not in {"saved_generated_output", "user_supplied_generated_output"}:
        raise ValueError("Label actual outputs explicitly; synthetic fixtures are not generation evidence")
    abilities = {row["id"]: row for row in corpus["abilities"]}
    if len(abilities) != len(corpus["abilities"]):
        raise ValueError("Duplicate corpus identifiers")
    rows = review["abilities"]
    if len(rows) != len(abilities) or {row["id"] for row in rows} != abilities.keys():
        raise ValueError("Every sampled ability must be reviewed exactly once")
    findings, tested = [], 0
    for row in rows:
        source = abilities[row["id"]]
        if not all(isinstance(row.get(key), str) and row[key].strip()
                   for key in ("role", "clarity", "finding", "evidence")):
            raise ValueError("Record role, clarity, finding and a source excerpt")
        if row["evidence"] not in source["text"]:
            raise ValueError("Review evidence must occur in the actual ability text")
        scenarios = row.get("scenarios", {})
        if source.get("utility") and set(scenarios) != set(SCENARIOS):
            raise ValueError("Utility needs all four ordinary-use scenario judgments")
        for scenario, judgment in scenarios.items():
            if scenario not in SCENARIOS or judgment.get("verdict") not in VERDICTS or not judgment.get("reason", "").strip():
                raise ValueError("Scenario judgments need a supported status and explanation")
            tested += 1
        findings.append({"id": row["id"], "name": source["name"], **row})
    return {"reviewer": review["reviewer"], "sampled_abilities": len(abilities),
            "utility_scenario_judgments": tested, "findings": findings,
            "kit_review": review["kits"], "skipped_samples": corpus.get("skipped_samples", []),
            "scope": "Single qualitative review of saved outputs; no independent raters, new generation, live play, balance or long-campaign reliability measurement",
            "model_calls": 0, "campaign_writes": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("corpus", "review", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.corpus.read_text(encoding="utf-8")),
                      json.loads(args.review.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Reviewed {result['sampled_abilities']} actual abilities; {result['utility_scenario_judgments']} Utility scenarios; no model calls or campaign writes")


if __name__ == "__main__":
    main()
