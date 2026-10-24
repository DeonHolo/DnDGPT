"""Development-only, evidence-based reviews across both games. No gameplay calls."""
import argparse
import json
from pathlib import Path

from app.game_profiles import AGE, SOVEREIGN

SCENARIOS = {"exploration", "conversation", "combat", "escape", "recovery"}
UTILITY_CASES = {"travel", "shelter_and_repairs", "information", "helping_people"}
VERDICTS = {"supported", "conditional", "unsupported", "unclear"}


def evaluate(corpus, review):
    if corpus.get("provenance") not in {"saved_generated_output", "development_generated_output"}:
        raise ValueError("Record actual output provenance; synthetic harness cases are not play evidence")
    if not corpus.get("generated_by") or not review.get("reviewer"):
        raise ValueError("Name the generator and reviewer")
    kits = {row["id"]: row for row in corpus["kits"]}
    if len(kits) != len(corpus["kits"]) or {k["game_id"] for k in kits.values()} != {AGE, SOVEREIGN}:
        raise ValueError("Include distinct fresh kits from both games")
    reviewed = review["kits"]
    if len(reviewed) != len(kits) or {r["id"] for r in reviewed} != kits.keys():
        raise ValueError("Review every kit exactly once")
    findings, cases = [], 0
    for row in reviewed:
        kit = kits[row["id"]]
        text = kit["text"]
        if kit["game_id"] == SOVEREIGN:
            roles = {a.get("sovereign_role") for a in kit.get("abilities", []) if a.get("scope") == "sovereign" and a.get("activation") == "Passive"}
            if not {"domain", "general", "army"} <= roles:
                findings.append({"kit": row["id"], "finding": "Missing explicit passive Domain, General or Army foundations"})
        for key in ("class_identity", "redundancy", "evolution_difference"):
            detail = row.get(key, {})
            if not detail.get("finding") or not detail.get("evidence") or detail["evidence"] not in text:
                raise ValueError("Identity, redundancy and evolution findings require exact source evidence")
        if set(row.get("scenarios", {})) != SCENARIOS:
            raise ValueError("Review all five play situations")
        groups = [row["scenarios"]]
        utilities = {u["id"]: u for u in kit["utilities"]}
        if len(utilities) < 2 or len(utilities) != len(kit["utilities"]) or set(row.get("utilities", {})) != utilities.keys():
            raise ValueError("Review each distinct Utility, with at least two per kit")
        for identity, judgments in row["utilities"].items():
            if set(judgments) != UTILITY_CASES:
                raise ValueError("Review each Utility in four ordinary situations")
            for result in judgments.values():
                if result.get("evidence", "") not in utilities[identity]["text"]:
                    raise ValueError("Utility evidence must occur in its actual rules")
            if sum(j.get("verdict") in {"supported", "conditional"} for j in judgments.values()) < 3:
                findings.append({"kit": row["id"], "utility": identity, "finding": "Fewer than three ordinary applications; revise before offering"})
            groups.append(judgments)
        for group in groups:
            for result in group.values():
                if result.get("verdict") not in VERDICTS or not result.get("reason") or not result.get("evidence") or result["evidence"] not in text:
                    raise ValueError("Each verdict needs a reason and exact source evidence")
                cases += 1
        for finding in row.get("findings", []):
            if not finding.get("finding") or not finding.get("evidence") or finding["evidence"] not in text:
                raise ValueError("A generation defect needs exact source evidence")
            findings.append({"kit": row["id"], **finding})
    return {"kits": len(kits), "scenario_judgments": cases, "reviewer": review["reviewer"],
            "generated_by": corpus["generated_by"], "provenance": corpus["provenance"], "findings": findings,
            "scope": "Recorded qualitative review; not independent judging, legal character creation, actual campaign play or a balance score",
            "ready_for_offer": not findings, "model_calls_during_gameplay": 0, "player_campaigns_accessed": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("corpus", "review", "output"):
        parser.add_argument("--"+key, type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.corpus.read_text(encoding="utf-8")), json.loads(args.review.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
