"""Private pre-roll design evidence; never a semantic originality oracle."""
from dataclasses import dataclass
import hashlib
from itertools import combinations
import json

from .contracts import construct, items, sequence, text


@dataclass(frozen=True)
class Concept:
    id: str
    name: str
    # Law, turn loop, resource cycle, space/targets, utility, counterplay, theme.
    fingerprint: tuple[str, str, str, str, str, str, str]
    summoner: bool = False
    parent_id: str | None = None

    def __post_init__(self):
        text(self.id, "concept id")
        text(self.name, "concept name")
        for part in items(self.fingerprint, "fingerprint", 7):
            text(part, "fingerprint component")
        if type(self.summoner) is not bool:
            raise ValueError("summoner must be boolean")
        if self.parent_id is not None:
            text(self.parent_id, "parent id")


def fingerprint(concept):
    return tuple(" ".join(part.casefold().split()) for part in concept.fingerprint[:6])


@dataclass(frozen=True)
class Decision:
    seed_id: str
    selected: bool
    reason: str

    def __post_init__(self):
        text(self.seed_id, "seed id")
        text(self.reason, "selection/rejection reason")
        if type(self.selected) is not bool:
            raise ValueError("Seed decision must be boolean")


@dataclass(frozen=True)
class Difference:
    left: str
    right: str
    permission: str
    economy: str
    tactical_decision: str
    independent_utility: str

    def __post_init__(self):
        for value in (self.left, self.right, self.permission, self.economy,
                      self.tactical_decision, self.independent_utility):
            text(value, "mechanical comparison evidence")
        if self.left == self.right:
            raise ValueError("Compare two distinct references")


@dataclass(frozen=True)
class KnownClass:
    draft_id: str
    concept: Concept

    def __post_init__(self):
        text(self.draft_id, "known creation draft")
        if type(self.concept) is not Concept:
            raise ValueError("Known history requires an actual saved concept")

    @property
    def reference(self):
        key = json.dumps([self.draft_id, self.concept.id], separators=(",", ":"))
        return "history-" + hashlib.sha256(key.encode()).hexdigest()


def typed(values, cls, minimum, maximum, name):
    if type(values) is not tuple or not minimum <= len(values) <= maximum or any(type(row) is not cls for row in values):
        raise ValueError("Invalid " + name)


@dataclass(frozen=True)
class ClassReview:
    seeds: tuple[Concept, ...]
    shortlist: tuple[str, ...]
    decisions: tuple[Decision, ...]
    differences: tuple[Difference, ...]
    history_differences: tuple[Difference, ...] = ()

    def __post_init__(self):
        typed(self.seeds, Concept, 12, 15, "private Class pool; require 12–15 seeds")
        items(self.shortlist, "Class shortlist", 5)
        if any(type(value) is not str for value in self.shortlist) or len(set(self.shortlist)) != 5:
            raise ValueError("Shortlist requires five distinct seed IDs")
        ids = {seed.id for seed in self.seeds}
        if len(ids) != len(self.seeds) or not set(self.shortlist) <= ids:
            raise ValueError("Private seeds require unique IDs and an actual five-seed shortlist")
        if any(seed.parent_id is not None for seed in self.seeds):
            raise ValueError("Class seeds cannot borrow a Background parent")
        typed(self.decisions, Decision, len(self.seeds), len(self.seeds), "complete seed decisions")
        if {row.seed_id for row in self.decisions} != ids or any(row.selected != (row.seed_id in self.shortlist) for row in self.decisions):
            raise ValueError("Every private seed needs its actual select/reject reason")
        typed(self.differences, Difference, 10, 10, "all ten finalist comparisons")
        actual = {frozenset((row.left, row.right)) for row in self.differences}
        if actual != {frozenset(pair) for pair in combinations(self.shortlist, 2)}:
            raise ValueError("Compare every finalist pair exactly once")
        typed(self.history_differences, Difference, 0, 10000, "known-history comparisons")

    def finalists(self):
        by_id = {seed.id: seed for seed in self.seeds}
        return tuple(by_id[identity] for identity in self.shortlist)

    def validate(self, concepts, history=()):
        typed(history, KnownClass, 0, 2000, "actual owned Class history")
        if len({row.reference for row in history}) != len(history):
            raise ValueError("Owned Class history references must be unique")
        if tuple(concepts) != self.finalists():
            raise ValueError("Rolled concepts must exactly match the reviewed shortlist in order")
        expected = {(identity, row.reference) for identity in self.shortlist for row in history}
        actual = {(row.left, row.right) for row in self.history_differences}
        if actual != expected or len(actual) != len(self.history_differences):
            raise ValueError("Compare each finalist with actual available owned Class history")
        prior = {fingerprint(row.concept) for row in history}
        if any(fingerprint(concept) in prior for concept in concepts):
            raise ValueError("Reject exact mechanical reuse of an actually saved prior Class")


def concept(value):
    return construct(Concept, value, {"fingerprint": sequence})


def known_class(value):
    return construct(KnownClass, value, {"concept": concept})


def review(value):
    return construct(ClassReview, value, {
        "seeds": lambda rows: tuple(concept(row) for row in sequence(rows)), "shortlist": sequence,
        "decisions": lambda rows: tuple(construct(Decision, row) for row in sequence(rows)),
        "differences": lambda rows: tuple(construct(Difference, row) for row in sequence(rows)),
        "history_differences": lambda rows: tuple(construct(Difference, row) for row in sequence(rows))})
