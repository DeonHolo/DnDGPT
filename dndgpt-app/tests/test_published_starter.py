import json

import httpx
import pytest

from app.adventure_library import CATALOG, read_section
from app.chat_game import ChatGame
from app.engine import EngineError
from app.library import Library
from app import published_starter as starter
from .test_dnd2024 import sheet, tool


def test_new_campaign_can_start_with_no_prepared_pack_or_extra_approval(engine, monkeypatch):
    monkeypatch.setattr(starter, "source_sections", lambda: pytest.fail("A campaign write must not download a source"))
    game = ChatGame(engine)
    state = game.create("owner-a", "Free starter", "free-starter-create", True, "dnd-2024")
    assert state["adventure"]["id"] == "frozen-sick"
    result = game.update("owner-a", state["id"], "free-starter-begin", 1, "Let's go", {
        "party": [sheet()], "party_mode": "solo", "opening_preview": "The hero arrives in Palebank Village.",
        "adventure": {"current_section": "MysteryinPalebankVillage"}}, True)["campaign"]
    assert result["phase"] == "adventure" and not result["paused"]
    assert result["adventure"]["title"] == "Frozen Sick"
    assert Library(engine).list("owner-a", "adventure") == []
    assert not result.get("pending_approvals")


def test_source_parser_keeps_only_the_article_and_chapter_boundaries():
    parser = starter.SourceParser()
    parser.feed('<nav>PRIVATE_TEST_NAV</nav><div class="p-article-content u-typography-format">'
                '<h1 id="FrozenSick">Frozen Sick</h1><p>Opening <em>story</em>.</p>'
                '<h2 id="StoryOverview">Story Overview</h2><div><p>GM secret <strong>clue</strong>.</p></div>'
                '<script>PRIVATE_TEST_SCRIPT</script><h2 id="CroakerCave">Croaker Cave</h2>'
                '<ul><li>First room</li><li>Second room</li></ul></div><footer>PRIVATE_TEST_FOOTER</footer>')
    assert set(parser.sections) == {"FrozenSick", "StoryOverview", "CroakerCave"}
    assert "Opening story." in parser.sections["FrozenSick"]
    assert "GM secret clue." in parser.sections["StoryOverview"]
    assert "• First room" in parser.sections["CroakerCave"]
    assert "PRIVATE_TEST" not in str(parser.sections)


def test_source_is_fetched_once_sections_are_private_and_index_is_offline(monkeypatch, engine):
    starter.source_sections.cache_clear()
    requests = []
    html = '<div class="p-article-content">'+''.join(
        f'<h2 id="{key}">{title}</h2><p>PRIVATE_TEST_SECRET {key} '+('detail ' * 30)+'</p>'
        for key, title in starter.CHAPTERS)+'</div><footer>not source</footer>'
    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "text/html"}, text=html)
    real_client = httpx.Client
    monkeypatch.setattr(starter.httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(respond)))
    library = Library(engine)
    try:
        index = read_section(library, "owner-a", "frozen-sick")
        assert requests == [] and "PRIVATE_TEST_SECRET" not in json.dumps(index)
        for key, _ in starter.CHAPTERS:
            result = read_section(library, "owner-a", "frozen-sick", key)
            assert "PRIVATE_TEST_SECRET" in result["section"]["content"]
            assert result["source_digest"]
        assert requests == [starter.SOURCE_URL]
        assert library.list("owner-a") == []
        assert CATALOG[0]["ready_to_play"] and not CATALOG[0]["source_required"]
    finally:
        starter.source_sections.cache_clear()


def test_publisher_outage_or_changed_layout_is_an_honest_recoverable_error(monkeypatch):
    starter.source_sections.cache_clear()
    real_client = httpx.Client
    monkeypatch.setattr(starter.httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text='<h1>Sign in</h1>'))))
    try:
        with pytest.raises(EngineError) as error:
            starter.read_starter("StoryOverview")
        assert error.value.status == 503
        assert "no upload" in str(error.value).lower()
        assert starter.read_starter()["id"] == "frozen-sick"
    finally:
        starter.source_sections.cache_clear()


def test_builtin_selection_is_validated_and_private_packs_still_require_owner(engine):
    game = ChatGame(engine)
    state = game.create("owner-a", "Starter", "starter-validation-create", True, "dnd-2024")
    for reference in ({"id": "frozen-sick", "version": 99}, {"id": "frozen-sick", "current_section": "invented"},
                      {"id": "somebody-elses-private-adventure"}):
        with pytest.raises(EngineError):
            game.update("owner-a", state["id"], "starter-invalid-reference", 1, "Invalid", {"adventure": reference})
        assert engine.get_campaign("owner-a", state["id"]) == state


def test_builtin_source_tool_is_model_only_and_catalog_has_a_playable_default(web):
    catalog = tool(web, "list_dnd_adventures", {})["structuredContent"]
    assert catalog["catalog"][0]["id"] == "frozen-sick"
    assert catalog["catalog"][0]["ready_to_play"]
    result = tool(web, "read_dnd_adventure", {"entry_id": "frozen-sick"})
    assert not result.get("isError")
    assert result["structuredContent"]["first_sections"]
    listing = web.post('/mcp', headers={"Accept": "application/json, text/event-stream"},
                       json={"jsonrpc":"2.0","id":1,"method":"tools/list"}).json()
    reference = next(t for t in listing["result"]["tools"] if t["name"] == "read_dnd_adventure")
    assert reference["_meta"]["ui"]["visibility"] == ["model"]
