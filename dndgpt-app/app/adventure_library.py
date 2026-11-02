"""Private GM sources and public adventure progress are deliberately separate."""
import copy
from urllib.parse import urlsplit

from .engine import fail
from .published_starter import STARTER, STARTER_ID, read_starter, starter_entry

CATALOG = [STARTER,
           {"id": "original-forgotten-realms", "title": "An original Forgotten Realms adventure",
            "adventure_type": "original", "recommended": False, "source_required": False,
            "setting": "Forgotten Realms", "summary": "Your GM prepares a new adventure grounded in official setting references."}]

SETTING_RESOURCES = {
    "setting": "Forgotten Realms", "default_region": "Sword Coast",
    "summary": "Faerûn offers established cities, frontiers, wilderness and ruins. The Sword Coast includes Waterdeep, Neverwinter and Baldur's Gate. Choose a specific starting region and an appropriate campaign date; keep established geography and factions consistent. Create local people and conflicts for this adventure, and distinguish them from published lore.",
    "sources": [
        {"title": "Official Forgotten Realms introduction", "url": "https://www.dndbeyond.com/resources/2037-the-forgotten-realms"},
        {"title": "Official regional adventure primer", "url": "https://www.dndbeyond.com/posts/2079-from-icewind-dale-to-calimport-a-sandbox-of"}],
    "preparation": "Consult the linked official material when available. Save the relevant setting facts, sources, locations, NPC goals, clues, encounter references, treasure and a definite ending in one private adventure pack. During play retrieve the current section plus linked sections as needed. The saved pack guides continuity; player actions can change its outcomes."}


def validate_adventure(value):
    from .chat_game import bounded_json
    bounded_json(value)
    if type(value) is not dict or value.keys() - {"title", "name", "summary", "setting", "region", "campaign_date", "adventure_type", "source_url", "credit", "sections", "starting_level", "ending_level", "party_size", "references"}:
        fail(422, "invalid_adventure", "Use the adventure pack fields from the D&D creation guide")
    result = copy.deepcopy(value)
    for key in ("title", "summary", "setting"):
        if type(result.get(key)) is not str or not result[key].strip() or len(result[key]) > 4000:
            fail(422, "invalid_adventure", "Include an adventure title, summary and setting")
    if result.get("adventure_type") not in {"published", "original"}:
        fail(422, "invalid_adventure", "Choose a published or original adventure")
    if result["adventure_type"] == "published":
        parsed = urlsplit(result.get("source_url", ""))
        if parsed.scheme != "https" or not parsed.netloc or not str(result.get("credit", "")).strip():
            fail(422, "adventure_source_required", "Record the published source and its credit")
    sections = result.get("sections")
    if type(sections) is not list or not 1 <= len(sections) <= 80:
        fail(422, "invalid_adventure", "Include 1..80 named GM reference sections")
    ids = []
    for section in sections:
        if type(section) is not dict or section.keys() - {"id", "title", "content", "player_summary", "links"}:
            fail(422, "invalid_adventure", "A section needs id, title, content, optional player_summary and links")
        for key in ("id", "title", "content"):
            if type(section.get(key)) is not str or not section[key].strip() or len(section[key]) > (50000 if key == "content" else 128):
                fail(422, "invalid_adventure", "Each section needs a stable ID, title and GM reference text")
        if "player_summary" in section and type(section["player_summary"]) is not str:
            fail(422, "invalid_adventure", "Player summary must be text")
        ids.append(section["id"])
    if len(set(ids)) != len(ids) or any(type(s.get("links", [])) is not list or any(x not in ids for x in s.get("links", [])) for s in sections):
        fail(422, "invalid_adventure", "Use unique section IDs and links to existing sections")
    for key in ("starting_level", "ending_level"):
        if key in result and (type(result[key]) is not int or not 1 <= result[key] <= 20):
            fail(422, "invalid_adventure", "Adventure levels range from 1 to 20")
    return result


def read_section(library, owner, entry_id, section_id=None, version=None):
    if entry_id == STARTER_ID:
        return read_starter(section_id, version)
    entry = library.get(owner, entry_id, version)
    if entry["kind"] != "adventure":
        fail(422, "adventure_required", "Choose a saved adventure pack")
    content = entry["content"]
    if section_id is None:
        return {"id": entry_id, "version": entry["version"], "title": content["title"],
                "setting": content["setting"], "summary": content["summary"],
                "sections": [{"id": s["id"], "title": s["title"], "links": s.get("links", [])} for s in content["sections"]]}
    section = next((s for s in content["sections"] if s["id"] == section_id), None)
    if section is None:
        fail(404, "not_found", "Adventure section not found")
    return {"adventure_id": entry_id, "version": entry["version"], "section": copy.deepcopy(section),
            "visibility": "GM reference; reveal only what the party discovers"}


def adventure_entry(library, db, owner, entry_id, version=None):
    """Built-in public metadata or an owner-checked private pack; never network in a write."""
    if entry_id == STARTER_ID:
        return starter_entry(version)
    return library._get(db, owner, entry_id, version)

