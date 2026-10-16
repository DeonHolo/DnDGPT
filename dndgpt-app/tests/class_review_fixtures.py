"""Explicit design-evidence fixtures, never a production Class generator."""
from dataclasses import asdict
from itertools import combinations
import json

from app.class_preparation import ClassReview, Concept, Decision, Difference
from app.storage import canonical


def difference(left, right):
    return Difference(left, right, "Fixture permission comparison", "Fixture cost comparison",
                      "Fixture tactical comparison", "Fixture independent utility comparison")


def review_for(finalists, history=(), size=12):
    seeds = (*finalists, *(Concept(f"rejected-fixture-{i}", f"Private rejected fixture {i}",
        tuple(f"Rejected fixture {i} component {part}" for part in range(7)))
        for i in range(size - len(finalists))))
    shortlist = tuple(row.id for row in finalists)
    return ClassReview(seeds, shortlist,
        tuple(Decision(row.id, row.id in shortlist, "Fixture selected reason" if row.id in shortlist
                       else "Fixture rejected reason") for row in seeds),
        tuple(difference(left, right) for left, right in combinations(shortlist, 2)),
        tuple(difference(identity, row.reference) for identity in shortlist for row in history))


def roll_payload(kind, choices, history=()):
    payload = {"kind": kind, "concepts": [asdict(row) for row in choices]}
    if kind == "classes":
        payload["review"] = asdict(review_for(choices, history))
    return json.loads(canonical(payload))
