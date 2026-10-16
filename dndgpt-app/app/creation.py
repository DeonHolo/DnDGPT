"""Pure creation contracts from rulebook sections 5–12 and hardener section 1.

This foundation is not exposed as a tool or a playable campaign. Structural
validation cannot certify creative originality, tier strength, or arbitrary
described effects; those still require validated mechanics before execution.
"""
from dataclasses import asdict, dataclass, replace

from .rules import ATTRIBUTES, RARITIES, Dice, derived, integer
from .powers import Rider, bind, integrate
from .gear import Loadout, calculate


from .abilities import Ability, preview as power_preview
from .contracts import text, items



from .class_preparation import Concept, ClassReview, KnownClass, fingerprint


@dataclass(frozen=True)
class Imprint:
    # No separate activation, resource cost, cooldown, or charge pool exists.
    parent_id: str
    modification: str
    limits: str
    rider: Rider | None = None

    def __post_init__(self):
        for name in ("parent_id", "modification", "limits"):
            text(getattr(self, name), name)
        if self.rider is not None and type(self.rider) is not Rider:
            raise ValueError("Imprint requires a typed integrated rider")


@dataclass(frozen=True)
class Offer:
    candidate_id: str
    rarity: str
    abilities: tuple[Ability, ...] = ()
    # Tier reason, ordinary trigger, lower-tier counterfactual, actual bounds.
    certification: tuple[str, str, str, str] = ()
    identity: str | None = None
    imprint: Imprint | None = None
    world_footprint: str | None = None

    def __post_init__(self):
        text(self.candidate_id, "candidate id")
        if self.rarity not in RARITIES:
            raise ValueError("Invalid rarity")
        for part in items(self.certification, "certification", 4):
            text(part, "certification component")
        if not all(isinstance(power, Ability) for power in items(self.abilities, "abilities")):
            raise ValueError("Abilities must use the typed ability contract")


@dataclass(frozen=True)
class Candidate:
    concept: Concept
    receipt: tuple

    @property
    def rarity(self):
        return dict(self.receipt)["final_rarity"]


@dataclass(frozen=True)
class Board:
    kind: str
    candidates: tuple[Candidate, ...]
    offers: tuple[Offer, ...] = ()


@dataclass(frozen=True)
class Draft:
    world_preview: str
    phase: str = "luck"
    version: int = 1
    luck_points: int | None = None
    luck_defaulted: bool = False
    boards: tuple[Board, ...] = ()
    selections: tuple = ()
    attributes: tuple = ()
    character_name: str | None = None
    opening_preview: str | None = None
    private_opening: tuple = ()
    loadout: Loadout | None = None
    class_review: ClassReview | None = None
    class_context: tuple[KnownClass, ...] = ()

    def __post_init__(self):
        text(self.world_preview, "world preview")
        if self.loadout is not None and type(self.loadout) is not Loadout:
            raise ValueError("Starting equipment requires a typed loadout")
        if self.class_review is not None and type(self.class_review) is not ClassReview:
            raise ValueError("Class preparation requires a typed private review")
        if type(self.class_context) is not tuple or any(type(row) is not KnownClass for row in self.class_context):
            raise ValueError("Class history requires actual owned draft references")


PHASES = {"classes": "class", "signatures": "signatures_titles",
          "titles": "signatures_titles", "backgrounds": "background_attributes"}


def require(draft, phase):
    if draft.phase != phase:
        raise ValueError(f"Requires {phase}; current phase is {draft.phase}")


def step(draft, **changes):
    return replace(draft, version=draft.version + 1, **changes)


def allocate_luck(draft, points=None, *, explicitly_defaulted=False):
    require(draft, "luck")
    if type(explicitly_defaulted) is not bool:
        raise ValueError("Default decision must be boolean")
    if points is None:
        if not explicitly_defaulted:
            raise ValueError("Wait for the player's Luck choice or explicit default")
        points = 0
    elif explicitly_defaulted:
        raise ValueError("Do not combine an allocation with a default decision")
    integer(points, 0, 4, "pre-awakening Luck points")
    return step(draft, phase="class", luck_points=points,
                luck_defaulted=explicitly_defaulted)


def board(draft, kind, *, complete=False):
    found = next((entry for entry in draft.boards if entry.kind == kind), None)
    if found is None or (complete and not found.offers):
        raise ValueError(f"{kind} board is not complete")
    return found


def owned_abilities(draft):
    owned = []
    for kind, selected in draft.selections:
        if kind == "backgrounds":
            continue
        for offer in board(draft, kind, complete=True).offers:
            if offer.candidate_id in selected:
                owned.extend(offer.abilities)
    return tuple(owned)


def validate_board(draft, kind, concepts, review=None, history=()):
    """Validate every candidate before asking for approval or consuming RNG."""
    if kind not in PHASES:
        raise ValueError("Unknown creation board")
    require(draft, PHASES[kind])
    if any(entry.kind == kind for entry in draft.boards):
        raise ValueError("Board already rolled; retain its original receipts")
    items(concepts, "concepts", 5)
    if not all(isinstance(concept, Concept) for concept in concepts):
        raise ValueError("Every candidate needs a typed concept")
    if len({concept.id for concept in concepts}) != 5:
        raise ValueError("Candidate IDs must be distinct")
    # Exact structural duplicate detection is not a semantic originality oracle.
    fingerprints = {fingerprint(concept) for concept in concepts}
    if len(fingerprints) != 5:
        raise ValueError("Reject mechanical reskins before rolling")
    if kind == "classes" and not any(concept.summoner for concept in concepts):
        raise ValueError("Class board requires a summoner concept")
    parents = {power.id for power in owned_abilities(draft)}
    for concept in concepts:
        if kind == "backgrounds" and concept.parent_id not in parents:
            raise ValueError("Background must target an actually owned parent")
        if kind != "backgrounds" and concept.parent_id is not None:
            raise ValueError("Only Background concepts select an Imprint parent")
    if kind == "classes":
        if type(review) is not ClassReview:
            raise ValueError("Class rolls require the private 12–15-seed review first")
        review.validate(concepts, history)
    elif review is not None:
        raise ValueError("Only Class rolling accepts a Class review")


def roll_board(draft, kind, concepts, dice: Dice, review=None, history=()):
    validate_board(draft, kind, concepts, review, history)
    candidates = tuple(Candidate(concept, tuple(dice.rarity(5 + draft.luck_points).items()))
                       for concept in concepts)
    changes = {"class_review": review, "class_context": tuple(history)} if kind == "classes" else {}
    return step(draft, boards=(*draft.boards, Board(kind, candidates)), **changes)


def validate_offer_programs(draft, offer):
    for power in offer.abilities:
        bind(power)
    if offer.imprint is not None:
        parent = next((power for power in owned_abilities(draft) if power.id == offer.imprint.parent_id), None)
        if parent is None:
            raise ValueError("Imprint program requires its actually owned parent")
        integrate(parent, offer.imprint.rider)


def board_programs(draft, entry):
    issues = []
    for offer in entry.offers:
        try:
            validate_board_offer(draft, entry, offer)
        except ValueError as error:
            issues.append({"candidate_id": offer.candidate_id, "detail": str(error)})
    return {"offers_checked": len(entry.offers), "programs_validated": len(entry.offers) == 5 and not issues,
            "semantic_tier_certification": False, "issues": issues}


def validate_board_offer(draft, entry, offer):
    validate_offer_programs(draft, offer)
    candidate = next(row for row in entry.candidates if row.concept.id == offer.candidate_id)
    if entry.kind == "classes" and candidate.concept.summoner and not any(bind(power).summon is not None for power in offer.abilities):
        raise ValueError("A declared summoner requires an actual supported summoning program")


def complete_board(draft, kind, offers):
    if kind not in PHASES:
        raise ValueError("Unknown creation board")
    require(draft, PHASES[kind])
    current = board(draft, kind)
    if current.offers:
        raise ValueError("Displayed offers are immutable; correction needs a separate workflow")
    items(offers, "offers", 5)
    if not all(isinstance(offer, Offer) for offer in offers):
        raise ValueError("Every offer must use the typed contract")
    if {offer.candidate_id for offer in offers} != {c.concept.id for c in current.candidates}:
        raise ValueError("Offers must match exactly the five fixed candidates")
    by_id = {offer.candidate_id: offer for offer in offers}
    seen = {power.id for entry in draft.boards for offer in entry.offers
            for power in offer.abilities}
    for candidate in current.candidates:
        offer = by_id[candidate.concept.id]
        if offer.rarity != candidate.rarity:
            raise ValueError("Cannot change a rolled rarity during certification")
        if kind == "backgrounds":
            text(offer.identity, "Background Identity")
            text(offer.world_footprint, "World Footprint")
            if (offer.abilities or not isinstance(offer.imprint, Imprint) or
                    offer.imprint.parent_id != candidate.concept.parent_id):
                raise ValueError("Background has exactly one integrated owned-source Imprint")
            validate_board_offer(draft, current, offer)
            continue
        if offer.imprint is not None or offer.identity is not None or offer.world_footprint is not None:
            raise ValueError("Background fields cannot grant powers to other sources")
        if not offer.abilities or (kind == "signatures" and len(offer.abilities) != 1):
            raise ValueError("Each source needs its actual powers; a Signature is one power")
        source_kind = {"classes": "CLASS", "signatures": "SIGNATURE", "titles": "TITLE"}[kind]
        for power in offer.abilities:
            if (power.source_kind != source_kind or power.source_id != offer.candidate_id or
                    power.rarity != offer.rarity or power.id in seen):
                raise ValueError("Invalid ability identity, provenance, rarity or duplicate ID")
            seen.add(power.id)
        if (kind == "classes" and RARITIES.index(offer.rarity) >= RARITIES.index("EPIC") and
                not any(power.activation == "FREE_ACTION" for power in offer.abilities)):
            raise ValueError("EPIC+ requires a class-native starting Free Action")
        validate_board_offer(draft, current, offer)
    completed = replace(current, offers=tuple(by_id[c.concept.id] for c in current.candidates))
    return step(draft, boards=tuple(completed if entry.kind == kind else entry
                                   for entry in draft.boards))


def select(draft, kind, ids):
    available = {offer.candidate_id for offer in board(draft, kind, complete=True).offers}
    if len(ids) != len(set(ids)) or not set(ids) <= available:
        raise ValueError("Choose distinct IDs from the actual offered board")
    return kind, tuple(ids)


def choose_class(draft, candidate_id):
    require(draft, "class")
    return step(draft, phase="signatures_titles",
                selections=(select(draft, "classes", (candidate_id,)),))


def choose_sources(draft, signature_ids, title_id):
    require(draft, "signatures_titles")
    items(signature_ids, "selected Signatures", 2)
    signatures = select(draft, "signatures", signature_ids)
    # The five Title offers must exist even if the player chooses NONE.
    titles = select(draft, "titles", () if title_id is None else (title_id,))
    return step(draft, phase="background_attributes",
                selections=(*draft.selections, signatures, titles))


def choose_background(draft, candidate_id, allocation, *, name=None):
    require(draft, "background_attributes")
    chosen = select(draft, "backgrounds", (candidate_id,))
    if type(allocation) is not dict or set(allocation) != set(ATTRIBUTES):
        raise ValueError("Allocate points across exactly the five attributes")
    for key in ATTRIBUTES:
        integer(allocation[key], 0, 4, key)
    if sum(allocation.values()) != 6 - draft.luck_points:
        raise ValueError("Spend exactly the remaining six minus committed Luck points")
    attributes = {key: 5 + allocation[key] + (draft.luck_points if key == "LCK" else 0)
                  for key in ATTRIBUTES}
    if max(attributes.values()) > 9:
        raise ValueError("Starting attribute maximum is 9, including committed Luck")
    if name is not None:
        text(name, "character name")
    return step(draft, phase="character_confirmation", attributes=tuple(attributes.items()),
                character_name=name, selections=(*draft.selections, chosen))


def starting_preview(draft):
    if draft.loadout is None:
        raise ValueError("Complete the starting build before character confirmation")
    attributes = dict(draft.attributes)
    result = calculate(draft.loadout, attributes)
    selected = dict(draft.selections)
    sources = {}
    background = None
    for kind in ("classes", "signatures", "titles", "backgrounds"):
        entry = board(draft, kind, complete=True)
        names = {candidate.concept.id: candidate.concept.name for candidate in entry.candidates}
        chosen = [offer for offer in entry.offers if offer.candidate_id in selected.get(kind, ())]
        expected = {"classes": 1, "signatures": 2, "titles": len(selected.get("titles", ())), "backgrounds": 1}[kind]
        if len(chosen) != expected or (kind == "titles" and expected not in (0, 1)):
            raise ValueError("Starting build requires all locked source selections")
        sources[kind] = [{"id": offer.candidate_id, "name": names[offer.candidate_id], "rarity": offer.rarity}
                         for offer in chosen]
        if kind == "backgrounds":
            if len(chosen) != 1:
                raise ValueError("Starting build requires the selected Background")
            background = chosen[0]
            if type(background.imprint) is not Imprint:
                raise ValueError("Starting Background requires its integrated Imprint")
            sources[kind][0].update(identity=background.identity, world_footprint=background.world_footprint)
    powers = owned_abilities(draft)
    power_ids = [power.id for power in powers]
    power_ids.extend(power.ability.id for item in (*draft.loadout.items, *draft.loadout.supplies) for power in item.powers)
    if len(power_ids) != len(set(power_ids)):
        raise ValueError("Starting source and item powers require distinct IDs")
    parent = next((power for power in powers if power.id == background.imprint.parent_id), None)
    if parent is None:
        raise ValueError("Starting Imprint parent is not actually owned")
    integrate(parent, background.imprint.rider)
    result["abilities"] = []
    for power in powers:
        program = bind(power)
        if any(attributes[key] < minimum for key, minimum in program.minimum_attributes):
            raise ValueError("Starting ability attribute prerequisite is unmet")
        record = power_preview(power, attributes)
        if power.id == parent.id:
            record["imprint"] = asdict(background.imprint)
        result["abilities"].append(record)
    result.update(character_name=draft.character_name, attributes=attributes, sources=sources,
                  executable_programs_validated=True, semantic_tier_certification=False)
    return result


def validate_starting_build(draft):
    if draft.class_review is None:
        raise ValueError("Pre-roll Class review is absent; legacy drafts cannot be silently backfilled")
    draft.class_review.validate(tuple(row.concept for row in board(draft, "classes").candidates), draft.class_context)
    for kind in PHASES:
        for offer in board(draft, kind, complete=True).offers:
            validate_board_offer(draft, board(draft, kind, complete=True), offer)
    return starting_preview(draft)


def prepare_starting_build(draft, loadout):
    require(draft, "character_confirmation")
    candidate = replace(draft, loadout=loadout)
    validate_starting_build(candidate)
    return step(candidate)


def confirm_character(draft, *, confirmed):
    require(draft, "character_confirmation")
    if confirmed is not True:
        raise ValueError("Explicit character confirmation is required")
    validate_starting_build(draft)
    return step(draft, phase="opening_preparation")


def prepare_opening(draft, preview, private_commitment):
    require(draft, "opening_preparation")
    validate_starting_build(draft)
    text(preview, "opening preview")
    required = {"location", "local_date_time", "factions", "opposition",
                "hooks_and_rewards", "convergence_truth"}
    if type(private_commitment) is not dict or set(private_commitment) != required:
        raise ValueError("Opening needs all six private commitment groups")
    for value in private_commitment.values():
        text(value, "private commitment")
    return step(draft, phase="adventure_authorization", opening_preview=preview,
                private_opening=tuple(sorted(private_commitment.items())))


def authorize_adventure(draft, *, authorized):
    require(draft, "adventure_authorization")
    if authorized is not True:
        raise ValueError("Separate explicit adventure authorization is required")
    validate_starting_build(draft)
    # This pure contract does not create/resume a campaign or advance its clock.
    return step(draft, phase="adventure_authorized")


def public_preview(draft):
    boards = {}
    for entry in draft.boards:
        names = {candidate.concept.id: candidate.concept.name for candidate in entry.candidates}
        boards[entry.kind] = [{key: value for key, value in asdict(offer).items()
                               if key != "certification"} | {"name": names[offer.candidate_id]}
                              for offer in entry.offers]
    attributes = dict(draft.attributes)
    starting = starting_preview(draft) if draft.loadout is not None else None
    return {"version": draft.version, "phase": draft.phase, "world_preview": draft.world_preview,
            "luck_points": draft.luck_points, "luck_defaulted": draft.luck_defaulted,
            "boards": boards, "board_programs": {entry.kind: board_programs(draft, entry) for entry in draft.boards},
            "selections": dict(draft.selections),
            "character_name": draft.character_name, "attributes": attributes,
            "derived": starting["derived"] if starting else derived(attributes) if attributes else None,
            "starting_build": starting,
            "opening_preview": draft.opening_preview,
            "playable_campaign_created": False, "fictional_time_advanced": False}
