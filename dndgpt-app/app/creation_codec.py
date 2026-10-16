"""Strict JSON adapters for immutable creation contracts; no arbitrary patches."""
from dataclasses import asdict

from .contracts import construct, pairs, sequence
from .creation import Board, Candidate, Concept, Draft, Imprint, Offer
from .abilities import decode as ability
from .powers import rider
from .gear import decode as loadout
from .class_preparation import known_class, review


def concept(value):
    return construct(Concept, value, {"fingerprint": sequence})


def imprint(value):
    return construct(Imprint, value, {"rider": lambda row: None if row is None else rider(row)})


def offer(value):
    return construct(Offer, value, {
        "abilities": lambda rows: tuple(ability(row) for row in sequence(rows)),
        "certification": sequence,
        "imprint": lambda row: None if row is None else imprint(row)})


def encode(draft):
    return {"schema": 1, "draft": asdict(draft)}


def decode(value):
    if type(value) is not dict or set(value) != {"schema", "draft"} or type(value["schema"]) is not int or value["schema"] != 1:
        raise ValueError("Unsupported creation draft schema")

    def candidate(row):
        return construct(Candidate, row, {"concept": concept, "receipt": pairs})

    def board(row):
        return construct(Board, row, {
            "candidates": lambda rows: tuple(candidate(item) for item in sequence(rows)),
            "offers": lambda rows: tuple(offer(item) for item in sequence(rows))})

    return construct(Draft, value["draft"], {
        "boards": lambda rows: tuple(board(row) for row in sequence(rows)),
        "selections": lambda rows: tuple((key, sequence(ids)) for key, ids in pairs(rows)),
        "attributes": pairs, "private_opening": pairs,
        "loadout": lambda row: None if row is None else loadout(row),
        "class_review": lambda row: None if row is None else review(row),
        "class_context": lambda rows: tuple(known_class(row) for row in sequence(rows))})

