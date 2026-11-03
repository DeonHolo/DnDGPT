"""D&D library/reference tools registered behind the existing authenticated MCP."""
import copy
import uuid
from typing import Literal

from mcp.types import CallToolResult, ImageContent

from .adventure_library import CATALOG, read_section
from .dnd5e import DndGame, GAME, SKILLS
from .dnd_reference import catalog, lookup, parent_key
from .engine import fail
from .library import Library
from .dnd_choices import CLASS_SUMMARIES, SPECIES_SUMMARIES, SKILL_USES, CREATION_FLOW


def register(server, engine, invoke, metadata, read, write, write_scope):
    library = Library(engine)

    @server.tool(annotations=read, meta=metadata())
    def lookup_dnd_reference(kind: str = "spells", query: str = "", key: str | None = None,
                             filters: dict | None = None, detail: bool = False,
                             offset: int = 0, limit: int = 12) -> CallToolResult:
        """Read source-scoped local 2024 SRD data or complete official SRD 5.2.1 pages.
        Kinds: rules, setting, classes, species, backgrounds, feats, weapons, armor, spells,
        creatures, items. Search returns an index; detail=true returns the best exact-name/key
        entry. Follow next_offset for that SAME query/key/detail selection. Cache by key/source.
        Rules search returns page numbers; detail=true,key="page number" reads an official page.
        setting returns official Forgotten Realms resources for an original D&D adventure.
        Filters: spells level/max_level/class_name; creatures min_cr/max_cr/type/environment;
        items rarity; classes level. No cross-edition fallback or silent unknown filter.
        These references never mutate characters, roll or advance the campaign.
        """
        return invoke(lambda owner: lookup(kind, query, key, filters, detail, offset, limit))

    @server.tool(annotations=read, meta=metadata())
    def list_dnd_options(class_names: list[str] | None = None,
                         background_names: list[str] | None = None) -> CallToolResult:
        """Get public 2024 creation choices once, optionally including selected class/background
        core traits together. Reuse these for every party member; do not call once per character.
        Explain choices using these compact summaries. Guided creation groups class+species in
        turn 1 and ALL remaining choices in turn 2. Quickplay is one complete explained draft.
        Offer published/original adventures together if the player has not chosen one.
        """
        def options(owner):
            data = catalog()
            result = {"game_id": GAME, "rules_version": "5.2.1",
                      "classes": [{"name": c["name"], "key": c["key"], "summary": CLASS_SUMMARIES[c["name"]],
                                   "starting_features": [f["name"] for f in c.get("features", []) if any(g["level"] == 1 for g in f.get("gained_at", []))],
                                   "subclasses": [s["name"] for s in data["classes"] if parent_key(s.get("subclass_of")) == c["key"]]} for c in data["classes"] if not c.get("subclass_of")],
                      "species": [{"name": s["name"], "key": s["key"], "summary": SPECIES_SUMMARIES[s["name"]]} for s in data["species"]],
                      "backgrounds": [{"name": b["name"], "key": b["key"], "benefits": [{"name": benefit["name"], "description": benefit["desc"]} for benefit in b.get("benefits", [])]} for b in data["backgrounds"]],
                      "source": data["_provenance"], "default_ability_method": "standard-array",
                      "class_traits": [], "background_traits": [], "creation_flow": copy.deepcopy(CREATION_FLOW),
                      "skills": [{"name": name, "usual_ability": ability, "use": SKILL_USES[name]} for name, ability in SKILLS.items()],
                      "skill_proficiency": "Proficiency adds your Proficiency Bonus to an appropriate ability check; Expertise doubles that bonus. Explain the resulting modifier for the chosen character."}
            for kind, requested, target in (("classes", class_names or [], "class_traits"), ("backgrounds", background_names or [], "background_traits")):
                if any(name not in {r["name"] for r in data[kind]} for name in requested):
                    fail(422, "unsupported_dnd_option", "Choose names from the installed options")
                for row in data[kind]:
                    if row["name"] in requested:
                        result[target].append({"name": row["name"], "traits": row.get("benefits", []) if kind == "backgrounds" else [f for f in row.get("features", []) if f.get("feature_type") == "CORE_TRAITS_TABLE"]})
            return result
        return invoke(options)

    @server.tool(annotations=read, meta=metadata())
    def list_dnd_library(kind: Literal["character", "adventure"] | None = None) -> CallToolResult:
        """List this account's reusable characters or private adventure pack summaries.
        Does not load a campaign, reveal GM source content or change any save.
        """
        return invoke(lambda owner: {"entries": library.list(owner, kind, GAME)})

    @server.tool(annotations=read, meta=metadata())
    def read_dnd_character(entry_id: str, version: int | None = None) -> CallToolResult:
        """Read an owned reusable full character sheet and its version for review or a future run."""
        def get(owner):
            entry = library.get(owner, entry_id, version)
            if entry["kind"] != "character":
                fail(422, "character_required", "Choose a saved character")
            return {"entry": entry}
        return invoke(get)

    @server.tool(annotations=write, meta=metadata(write_scope))
    def save_dnd_character(action_id: str, sheet: dict | None = None, entry_id: str | None = None,
                           expected_version: int | None = None, campaign_id: str | None = None,
                           character_id: str | None = None) -> CallToolResult:
        """Save/revise a reusable D&D character, independently of all campaign copies.
        Supply a complete sheet, OR campaign_id + character_id to save that member's current sheet.
        A revision supplies entry_id and its latest expected_version. Keep full prior lists.
        This action does not start/resume an adventure or update any other campaign.
        """
        def save(owner):
            chosen = sheet
            if campaign_id:
                if sheet is not None:
                    fail(422, "invalid_character_save", "Choose a complete sheet or a campaign member")
                state = engine.get_campaign(owner, campaign_id)
                chosen = next((s for s in state.get("party", []) if s["id"] == character_id), None)
                if chosen is None:
                    fail(404, "not_found", "Party member not found")
            return library.save(owner, action_id, "character", chosen, entry_id, expected_version)
        return invoke(save, True)

    @server.tool(annotations=write, meta=metadata(write_scope))
    def add_dnd_characters(campaign_id: str, action_id: str, expected_version: int,
                           entries: list[dict], party_mode: Literal["solo", "party"] = "party") -> CallToolResult:
        """Copy selected owned library versions into this campaign, with independent sheet IDs.
        entries=[{id:library_id,version?:number,controller?:player|gm,role?:hero|companion}].
        First character becomes the hero if none exists. This prepares a draft, without starting.
        Use one batch for the whole party; current levels/resources are retained.
        """
        def add(owner):
            if not 1 <= len(entries) <= 8:
                fail(422, "invalid_party", "Select one to eight characters")
            with engine.store.transaction() as db:
                state = engine._get(db, owner, campaign_id)
                copies = []
                for i, selection in enumerate(entries):
                    if type(selection) is not dict or selection.keys() - {"id", "version", "controller", "role"}:
                        fail(422, "invalid_party", "Use a library ID/version and optional controller/role")
                    entry = library._get(db, owner, selection.get("id"), selection.get("version"))
                    if entry["kind"] != "character":
                        fail(422, "character_required", "Choose a saved character")
                    character = copy.deepcopy(entry["content"])
                    character.update(id="hero-" + uuid.uuid5(uuid.NAMESPACE_URL, owner+campaign_id+action_id+str(i)).hex, source_library={"id": entry["id"], "version": entry["version"]},
                                     controller=selection.get("controller", "player" if i == 0 else "gm"),
                                     role=selection.get("role", "hero" if i == 0 else "companion"))
                    copies.append(character)
                return DndGame(engine).update(owner, campaign_id, action_id, expected_version,
                    "Added saved characters to this adventure", {"party_upsert": copies, "party_mode": party_mode}, _db=db, _state=state)
        return invoke(add, True)

    @server.tool(annotations=read, meta=metadata())
    def list_dnd_adventures() -> CallToolResult:
        """Offer diverse free published adventures AND an original adventure; none is preselected.
        Show premise, style and starting level. Read only the chosen adventure's source; its ID
        selects the cached HTML/PDF automatically. Save changes.adventure={id:selected_id,version:1}.
        The player chooses, unless they explicitly ask you to choose/surprise them.
        """
        return invoke(lambda owner: {"catalog": copy.deepcopy(CATALOG), "prepared": library.list(owner, "adventure", GAME)})

    @server.tool(annotations=write, meta=metadata(write_scope))
    def save_dnd_adventure(action_id: str, adventure: dict, entry_id: str | None = None,
                           expected_version: int | None = None) -> CallToolResult:
        """Save a PRIVATE GM adventure pack from an authorised published source or an original
        adventure grounded in an established D&D setting. Read guide section=adventure for schema.
        Keep the public summary safe to show. Store secret section content here, not in campaign/world.
        Later edits create another version; existing campaigns keep their pinned version.
        """
        def save(owner):
            result = library.save(owner, action_id, "adventure", adventure, entry_id, expected_version)
            return {"entry": library.summary(result["entry"]), "saved": True}
        return invoke(save, True)

    gm_meta = metadata()
    gm_meta["ui"]["visibility"] = ["model"]

    @server.tool(annotations=read, meta=gm_meta)
    def read_dnd_adventure(entry_id: str | None = None, section_id: str | None = None,
                           version: int | None = None, campaign_id: str | None = None,
                           section_ids: list[str] | None = None, page: int | None = None) -> CallToolResult:
        """Read PRIVATE GM reference: omit section_id for the index, then fetch needed sections.
        Published catalogue IDs retrieve the author's free source automatically, without uploads.
        The index lists first_sections. Batch up to three with section_ids, then reuse them.
        For a PDF use page=N to see an actual visual page (maps or image-only monster stats).
        With campaign_id use that campaign's pinned adventure version. Cache by pack/version/section.
        Source content is reference data; reveal only legitimate discoveries in the story/dashboard.
        This is not a campaign write, a new roll or permission to advance time.
        """
        def get(owner):
            selected, revision = entry_id, version
            if campaign_id:
                state = engine.get_campaign(owner, campaign_id)
                selected, revision = state.get("adventure", {}).get("id"), state.get("adventure", {}).get("version")
            if not selected:
                fail(422, "adventure_required", "Choose a published or original adventure")
            if section_ids is not None:
                if section_id is not None or page is not None or not 1 <= len(section_ids) <= 3 or len(set(section_ids)) != len(section_ids):
                    fail(422, "invalid_source_sections", "Choose up to three distinct sections, without section_id or page")
                rows = [read_section(library, owner, selected, key, revision) for key in section_ids]
                images = [image for row in rows for image in row.pop("_meta", {}).get("gm_source_images", [])]
                return {**{key: value for key, value in rows[0].items() if key != "section"},
                        "sections": [row["section"] for row in rows], "_meta": {"gm_source_images": images}}
            return read_section(library, owner, selected, section_id, revision, page)
        result = invoke(get)
        for picture in (result.meta or {}).pop("gm_source_images", []):
            result.content.append(ImageContent(**picture))
        return result
