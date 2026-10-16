"""Durable, owner-scoped creation drafts. No campaign or clock is created here.

Proposals are inert. App approval commits one transition and its receipt in the
same SQLite transaction. This development workflow does not certify playable kits.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import secrets
import time
import uuid

from . import creation as rules
from . import creation_codec as codec
from .class_preparation import KnownClass, review
from .engine import fail, identifier
from .rules import Dice, integer
from .storage import canonical

APPROVAL_TTL = 900
MAX_REQUEST_BYTES = 1_000_000
COMMANDS = {
    "allocate_luck": (set(), {"points", "explicitly_defaulted"}),
    "roll_board": ({"kind", "concepts"}, {"review"}),
    "complete_board": ({"kind", "offers"}, set()),
    "choose_class": ({"candidate_id"}, set()),
    "choose_sources": ({"signature_ids", "title_id"}, set()),
    "choose_background": ({"candidate_id", "allocation"}, {"name"}),
    "prepare_starting_build": ({"loadout"}, set()),
    "confirm_character": ({"confirmed"}, set()),
    "prepare_opening": ({"preview", "private_commitment"}, set()),
    "authorize_adventure": ({"authorized"}, set()),
}


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def command(kind, payload):
    if type(kind) is not str or kind not in COMMANDS or type(payload) is not dict:
        raise ValueError("Unknown creation command or invalid payload")
    required, optional = COMMANDS[kind]
    if not required <= payload.keys() or payload.keys() - required - optional:
        raise ValueError(f"Invalid {kind} fields")
    data = dict(payload)
    if kind == "roll_board":
        data["concepts"] = tuple(codec.concept(row) for row in codec.sequence(data["concepts"]))
        if data.get("review") is not None:
            data["review"] = review(data["review"])
    elif kind == "complete_board":
        data["offers"] = tuple(codec.offer(row) for row in codec.sequence(data["offers"]))
    elif kind == "choose_sources":
        data["signature_ids"] = codec.sequence(data["signature_ids"])
    elif kind == "prepare_starting_build":
        data["loadout"] = codec.loadout(data["loadout"])
    return data


def transition(draft, kind, payload, dice=None, history=()):
    data = command(kind, payload)
    if kind == "roll_board":
        rules.validate_board(draft, **data, history=history)
        return None if dice is None else rules.roll_board(draft, **data, dice=dice, history=history)
    return getattr(rules, kind)(draft, **data)


def view(draft_id, draft):
    return json.loads(canonical({"id": draft_id, **rules.public_preview(draft),
        "mode": "development_creation_draft", "playable": False}))


def preparation(draft, history=()):
    """Private GM authoring context, never raw or future rarity rolls."""
    def known(rows):
        return [{"reference": row.reference, **asdict(row)} for row in rows]
    return {"pending_boards": {entry.kind: [
        {"concept": asdict(candidate.concept), "rarity": candidate.rarity,
         "enhanced": dict(candidate.receipt)["enhanced"]}
        for candidate in entry.candidates] for entry in draft.boards if not entry.offers},
        "owned_abilities": [asdict(power) for power in rules.owned_abilities(draft)],
        "class_review": asdict(draft.class_review) if draft.class_review is not None else None,
        "class_review_context": known(draft.class_context),
        "known_classes": known(history),
        "history_scope": "Completed Class boards in this owner\u2019s other saved creation drafts only; no campaign imports or invented memory",
        "semantic_tier_certification": False,
        "certification": "Pre-roll design evidence and supported programs are required; semantic novelty/tier certification remains pending"}


class CreationRepository:
    def __init__(self, store, dice=None):
        self.store = store
        self.dice = dice or Dice()

    def _row(self, db, owner, draft_id):
        row = db.execute("SELECT * FROM creation_drafts_v1 WHERE id=? AND owner=?",
                         (draft_id, owner)).fetchone()
        if row is None:
            fail(404, "not_found", "Creation draft not found")
        return row

    def _get(self, db, owner, draft_id):
        row = self._row(db, owner, draft_id)
        try:
            data = json.loads(row["data"])
            last = db.execute("SELECT number,event FROM creation_events_v1 WHERE draft_id=? "
                              "ORDER BY number DESC LIMIT 1", (draft_id,)).fetchone()
            if (last is None or last["number"] != row["version"] or
                    json.loads(last["event"])["draft_sha256"] != digest(data)):
                raise ValueError("Draft receipt mismatch")
            draft = codec.decode(data)
            if type(draft.version) is not int or draft.version != row["version"]:
                raise ValueError("Draft version mismatch")
            return draft
        except (ValueError, TypeError, KeyError):
            fail(409, "integrity_error", "Stored creation draft failed integrity validation")

    def _class_history(self, db, owner, draft_id):
        rows = db.execute("SELECT id FROM creation_drafts_v1 WHERE owner=? AND id<>? ORDER BY rowid",
                          (owner, draft_id)).fetchall()
        result = []
        for row in rows:
            previous = self._get(db, owner, row["id"])
            for entry in previous.boards:
                if entry.kind == "classes" and entry.offers:
                    result.extend(KnownClass(row["id"], candidate.concept) for candidate in entry.candidates)
        return tuple(result)

    def _history_for(self, db, owner, draft_id, kind, payload):
        if kind == "roll_board" and type(payload) is dict and payload.get("kind") == "classes":
            return self._class_history(db, owner, draft_id)
        return ()

    def _pending_meta(self, db, owner, draft_id=None):
        query = "SELECT * FROM creation_proposals_v1 WHERE owner=? AND result IS NULL AND created_at>=?"
        args = [owner, time.time() - APPROVAL_TTL]
        if draft_id is not None:
            query += " AND draft_id=?"
            args.append(draft_id)
        rows = db.execute(query + " ORDER BY rowid DESC LIMIT 20", args).fetchall()
        approvals = [self._proposal(row).get("_meta", {}).get("creation_approval") for row in rows]
        return {"creation_approvals": [approval for approval in approvals if approval is not None]}

    def list_drafts(self, owner):
        with self.store.transaction() as db:
            rows = db.execute("SELECT id FROM creation_drafts_v1 WHERE owner=? "
                              "ORDER BY rowid DESC LIMIT 100", (owner,)).fetchall()
            drafts = [view(row["id"], self._get(db, owner, row["id"])) for row in rows]
            return {"drafts": drafts, "_meta": self._pending_meta(db, owner)}

    def get_draft(self, owner, draft_id, include_preparation=False):
        with self.store.transaction() as db:
            draft = self._get(db, owner, draft_id)
            result = {"draft": view(draft_id, draft),
                      "_meta": self._pending_meta(db, owner, draft_id)}
            if include_preparation:
                result["preparation"] = json.loads(canonical(preparation(
                    draft, self._class_history(db, owner, draft_id))))
            return result

    def _proposal(self, row):
        committed = row["result"] is not None
        expired = time.time() - row["created_at"] > APPROVAL_TTL
        proposal = {"id": row["id"], "draft_id": row["draft_id"],
                    "expected_version": row["expected_version"],
                    "preview": json.loads(row["preview"]),
                    "status": "committed" if committed else "expired" if expired else "pending"}
        result = {"proposal": proposal}
        if committed:
            result["committed"] = json.loads(row["result"])
        elif not expired:
            result["_meta"] = {"creation_approval": {
                "proposal": proposal, "approval_token": row["approval_token"]}}
        return result

    def _request(self, request):
        try:
            encoded = canonical(request)
            if len(encoded.encode()) > MAX_REQUEST_BYTES:
                raise ValueError("Creation request exceeds size limit")
            return encoded
        except (ValueError, TypeError):
            fail(422, "invalid_creation", "Creation request must be bounded JSON")

    def _prior(self, db, owner, action_id, request):
        row = db.execute("SELECT * FROM creation_proposals_v1 WHERE owner=? AND action_id=?",
                         (owner, action_id)).fetchone()
        if row and row["request"] != request:
            fail(409, "idempotency_conflict", "action_id already has different arguments")
        return row

    def _insert(self, db, owner, draft_id, action_id, version, request, preview):
        proposal_id, token = "creation-proposal-" + uuid.uuid4().hex, secrets.token_urlsafe(32)
        db.execute("INSERT INTO creation_proposals_v1 VALUES (?,?,?,?,?,?,?,?,?,NULL)",
                   (proposal_id, owner, draft_id, action_id, version, request,
                    canonical(preview), token, time.time()))
        return self._proposal(db.execute("SELECT * FROM creation_proposals_v1 WHERE id=?",
                                         (proposal_id,)).fetchone())

    def propose_start(self, owner, world_preview, action_id):
        identifier(action_id, "action_id")
        request = self._request({"kind": "start_creation", "world_preview": world_preview})
        with self.store.transaction() as db:
            prior = self._prior(db, owner, action_id, request)
            if prior:
                return self._proposal(prior)
            try:
                draft = rules.Draft(world_preview)
            except ValueError as error:
                fail(422, "invalid_creation", str(error))
            draft_id = "draft-" + uuid.uuid4().hex
            return self._insert(db, owner, draft_id, action_id, 0, request,
                                {"kind": "start_creation", "draft": view(draft_id, draft),
                                 "effect": "Create a development draft only; no campaign or rolls"})

    def propose_transition(self, owner, draft_id, action_id, expected_version, kind, payload):
        identifier(action_id, "action_id")
        identifier(draft_id, "draft_id")
        try:
            integer(expected_version, 1, 1_000_000, "expected_version")
        except ValueError as error:
            fail(422, "invalid_creation", str(error))
        request = self._request({"draft_id": draft_id, "expected_version": expected_version,
                                 "kind": kind, "payload": payload})
        with self.store.transaction() as db:
            draft = self._get(db, owner, draft_id)
            prior = self._prior(db, owner, action_id, request)
            if prior:
                return self._proposal(prior)
            if draft.version != expected_version:
                fail(409, "version_conflict", "Creation draft changed; inspect current state")
            try:
                history = self._history_for(db, owner, draft_id, kind, payload)
                proposed = transition(draft, kind, payload, history=history)
            except (ValueError, TypeError, KeyError) as error:
                fail(422, "invalid_creation", str(error))
            preview = {"kind": kind, "draft": view(draft_id, proposed or draft),
                       "effect": "Roll five fixed candidates after approval" if proposed is None
                                 else "Save this creation transition; no gameplay or time advancement"}
            return self._insert(db, owner, draft_id, action_id, expected_version, request, preview)

    def confirm(self, owner, proposal_id, approval_token):
        with self.store.transaction() as db:
            row = db.execute("SELECT * FROM creation_proposals_v1 WHERE id=? AND owner=?",
                             (proposal_id, owner)).fetchone()
            if row is None:
                fail(404, "not_found", "Creation proposal not found")
            if (type(approval_token) is not str or len(approval_token) > 256 or
                    not secrets.compare_digest(row["approval_token"].encode(), approval_token.encode())):
                fail(403, "approval_required", "Approve the exact creation proposal in the app")
            if row["result"] is not None:
                return json.loads(row["result"])
            if time.time() - row["created_at"] > APPROVAL_TTL:
                fail(409, "proposal_expired", "Creation approval expired; request a new preview")
            request = json.loads(row["request"])
            kind, draft_id = request["kind"], row["draft_id"]
            if kind == "start_creation":
                draft = rules.Draft(request["world_preview"])
                db.execute("INSERT INTO creation_drafts_v1 VALUES (?,?,?,?)",
                           (draft_id, owner, draft.version, canonical(codec.encode(draft))))
            else:
                current = self._get(db, owner, draft_id)
                if current.version != row["expected_version"]:
                    fail(409, "version_conflict", "Creation draft changed; inspect current state")
                try:
                    history = self._history_for(db, owner, draft_id, kind, request["payload"])
                    draft = transition(current, kind, request["payload"], self.dice, history)
                except (ValueError, TypeError, KeyError) as error:
                    fail(422, "invalid_creation", str(error))
                db.execute("UPDATE creation_drafts_v1 SET version=?,data=? WHERE id=? AND owner=?",
                           (draft.version, canonical(codec.encode(draft)), draft_id, owner))
            self._append(db, draft_id, draft, row, request)
            result = {"draft": view(draft_id, draft), "receipt": {
                "proposal_id": proposal_id, "action_id": row["action_id"],
                "kind": kind, "version": draft.version}}
            db.execute("UPDATE creation_proposals_v1 SET result=? WHERE id=?",
                       (canonical(result), proposal_id))
            return result

    def _append(self, db, draft_id, draft, proposal, request):
        last = db.execute("SELECT hash FROM creation_events_v1 WHERE draft_id=? "
                          "ORDER BY number DESC LIMIT 1", (draft_id,)).fetchone()
        previous = last["hash"] if last else "0" * 64
        event = {"kind": request["kind"], "version": draft.version, "phase": draft.phase,
                 "action_id": proposal["action_id"], "proposal_id": proposal["id"],
                 "approval": "app", "draft_sha256": digest(codec.encode(draft)),
                 "utc": datetime.now(timezone.utc).isoformat()}
        payload = request.get("payload", {})
        if request["kind"] == "roll_board":
            event["rolls"] = [{"candidate_id": candidate.concept.id, **dict(candidate.receipt)}
                              for candidate in rules.board(draft, payload["kind"]).candidates]
            if payload["kind"] == "classes":
                event["class_review_sha256"] = digest(asdict(draft.class_review))
                event["class_context_sha256"] = digest([asdict(row) for row in draft.class_context])
                event["private_seed_count"] = len(draft.class_review.seeds)
        elif request["kind"] == "prepare_opening":
            event["opening_commitment_sha256"] = digest(dict(draft.private_opening))
        elif request["kind"] == "complete_board":
            event["board"] = payload["kind"]
        else:
            event["decision"] = payload
        db.execute("INSERT INTO creation_events_v1 VALUES (?,?,?,?,?)",
                   (draft_id, draft.version, canonical(event), previous,
                    hashlib.sha256((previous + canonical(event)).encode()).hexdigest()))

    def audit(self, owner, draft_id, show_rolls=False):
        with self.store.transaction() as db:
            state = self._row(db, owner, draft_id)
            rows = db.execute("SELECT * FROM creation_events_v1 WHERE draft_id=? ORDER BY number",
                              (draft_id,)).fetchall()
            previous, valid, events = "0" * 64, True, []
            for number, row in enumerate(rows, 1):
                event = json.loads(row["event"])
                computed = hashlib.sha256((previous + canonical(event)).encode()).hexdigest()
                valid &= (row["number"] == number == event["version"] and
                          row["previous_hash"] == previous and row["hash"] == computed)
                previous = row["hash"]
                if not show_rolls and "rolls" in event:
                    event["rolls"] = [{key: roll[key] for key in ("candidate_id", "final_rarity", "enhanced")}
                                      for roll in event["rolls"]]
                events.append(event)
            valid &= bool(rows) and len(rows) == state["version"]
            if rows:
                valid &= json.loads(rows[-1]["event"])["draft_sha256"] == digest(json.loads(state["data"]))
            return {"draft_id": draft_id, "integrity_valid": bool(valid), "events": events}
