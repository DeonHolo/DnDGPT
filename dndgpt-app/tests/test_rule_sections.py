import hashlib
import json
from pathlib import Path

import pytest

from app.engine import EngineError
from app.mcp_server import rules_page
from app.rule_sections import sections, AMENDMENTS, SUBSECTIONS
from .test_server import rpc, tool


SOURCE = Path(__file__).resolve().parents[1] / "rules/rulebook-v1.0.txt"


def test_index_covers_every_chapter_and_required_current_amendment():
    text = SOURCE.read_bytes().decode()
    entries = sections(text)
    assert set(map(str, range(1, 47))) | {"32A"} | set(AMENDMENTS) | set(SUBSECTIONS) == set(entries)
    assert all(item["start"] < item["end"] for item in entries.values())
    index = rules_page("index", 0)
    assert index["next_offset"] is None
    assert "Finishing a section is not a complete manual read" in index["content"]
    assert "loading |" in index["content"] and "33 |" in index["content"]


@pytest.mark.parametrize("key", ["4", "8", "33", "38", "loading", "story", "creation-order", "utility", "continuity", "story-ui", "enemy-tactics"])
def test_section_pages_reassemble_exact_authoritative_slice(key):
    data = SOURCE.read_bytes()
    text = data.decode()
    item = sections(text)[key]
    offset, parts = 0, []
    while True:
        page = rules_page("rulebook", offset, key)
        assert page["section"] == key and page["scope"] == "section"
        assert page["source_sha256"] == hashlib.sha256(data).hexdigest()
        assert len(page["content"]) <= 8000
        parts.append(page["content"])
        if page["next_offset"] is None:
            break
        assert page["next_offset"] == offset + len(page["content"])
        offset = page["next_offset"]
    assert "".join(parts) == text[item["start"]:item["end"]]
    assert page["total_characters"] < page["source_characters"]


@pytest.mark.parametrize("document,section", [("rulebook", "../../.env"), ("hardener", "4"), ("index", "33")])
def test_invalid_section_cannot_select_arbitrary_content(document, section):
    with pytest.raises(EngineError, match="Choose a rulebook section"):
        rules_page(document, 0, section)


def test_indexed_read_works_through_authenticated_mcp_and_does_not_write(web):
    before = web.get("/api/campaigns").json()
    for section, heading in (("story", "Where this place met Earth"), ("utility", "Utility usefulness and creative application"),
                             ("enemy-tactics", "Enemy identity, adaptive tactics and visible voice")):
        result = tool(web, "read_rules", {"document": "rulebook", "section": section})
        assert not result.get("isError"), result
        assert heading in result["structuredContent"]["content"]
    assert web.get("/api/campaigns").json() == before
    schema = next(row for row in rpc(web, "tools/list")["tools"] if row["name"] == "read_rules")["inputSchema"]
    assert "index" in schema["properties"]["document"]["enum"]
    assert "section" in schema["properties"]


def test_full_glossary_survives_and_hardener_is_one_compact_page():
    hardener = rules_page("hardener", 0)
    assert hardener["next_offset"] is None
    assert len(json.dumps(hardener, ensure_ascii=False)) < 10000
    chapter = SOURCE.read_bytes().decode()
    excerpt = sections(chapter)["33"]
    glossary = chapter[excerpt["start"]:excerpt["end"]]
    for heading in ("1. Core Feature", "2. CRITICAL", "11. Persistence", "Standing inline-term"):
        assert heading in glossary


def test_routine_story_contract_fits_one_tool_response():
    page = rules_page("rulebook", 0, "story-ui")
    assert page["next_offset"] is None
    assert len(page["content"]) <= 8000
