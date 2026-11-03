import json
from io import BytesIO

import httpx
import pypdfium2 as pdfium
import pytest

from app.adventure_library import CATALOG, read_section
from app.chat_game import ChatGame
from app.engine import EngineError
from app.library import Library
from app import published_starter as reader
from app.published_catalog import ADVENTURES
from app.pdf_sources import extract_pages, needs_visual, render_page
from .test_dnd2024 import sheet, tool


@pytest.fixture(autouse=True)
def clear_sources():
    reader.source_sections.cache_clear(); render_page.cache_clear()
    yield
    reader.source_sections.cache_clear(); render_page.cache_clear()


@pytest.mark.parametrize("entry_id", list(ADVENTURES))
def test_player_can_pick_any_published_adventure_without_a_pack_or_extra_approval(engine, monkeypatch, entry_id):
    monkeypatch.setattr(reader, "source_sections", lambda *args: pytest.fail("A campaign write must not download a source"))
    game = ChatGame(engine)
    state = game.create("owner-a", "Adventure choice", "choice-create", True, "dnd-2024")
    assert state["adventure"] == {}
    book = ADVENTURES[entry_id]
    result = game.update("owner-a", state["id"], "choice-begin", 1, "Choose and let's go", {
        "party": [sheet(level=book["starting_level"])], "party_mode": "solo",
        "opening_preview": "The hero arrives at the chosen adventure's opening.",
        "adventure": {"id": entry_id, "current_section": book["_first_sections"][0]}}, True)["campaign"]
    assert result["phase"] == "adventure" and not result["paused"]
    assert result["adventure"]["id"] == entry_id
    assert result["adventure"]["title"] == book["title"]
    assert Library(engine).list("owner-a", "adventure") == []
    assert not result.get("pending_approvals")


def test_no_adventure_is_implicitly_chosen_when_start_is_incomplete(engine):
    game = ChatGame(engine)
    state = game.create("owner-a", "Unselected", "unselected-create", True, "dnd-2024")
    with pytest.raises(EngineError) as error:
        game.update("owner-a", state["id"], "unselected-start", 1, "Start", {
            "party": [sheet()], "party_mode": "solo", "opening_preview": "A draft opening"}, True)
    assert error.value.code == "incomplete_dnd_start"
    assert engine.get_campaign("owner-a", state["id"]) == state


def test_source_parser_keeps_article_boundaries_and_handles_unlabelled_blog_headings():
    parser = reader.SourceParser()
    parser.feed('<nav>PRIVATE_TEST_NAV</nav><div class="p-article-content u-typography-format">'
                '<h1 id="FrozenSick">Frozen Sick</h1><p>Opening <em>story</em>.</p>'
                '<h2 id="StoryOverview">Story Overview</h2><div><p>GM secret <strong>clue</strong>.</p></div>'
                '<script>PRIVATE_TEST_SCRIPT</script><h2 id="CroakerCave">Croaker Cave</h2>'
                '<ul><li>First room</li><li>Second room</li></ul></div><footer>PRIVATE_TEST_FOOTER</footer>')
    assert set(parser.sections) == {"FrozenSick", "StoryOverview", "CroakerCave"}
    assert "Opening story." in parser.sections["FrozenSick"]
    assert "GM secret clue." in parser.sections["StoryOverview"]
    assert "PRIVATE_TEST" not in str(parser.sections)
    blog = reader.SourceParser((("adventure-start", "Opening"), ("firejolt-cafe", "The café")))
    blog.feed('<section class="p-article-content"><h2>Adventure&nbsp;start</h2><p>Opening.</p>'
              '<h2>Firejolt <em>Café</em></h2><p>Location.</p></section><p>Comments stay outside.</p>')
    assert set(blog.sections) == {"adventure-start", "firejolt-cafe"}
    assert "Comments" not in str(blog.sections)


def html_for(book):
    return '<section class="p-article-content">' + ''.join(
        f'<h2 id="{key}">{title}</h2><p>PRIVATE_TEST_SECRET {book["id"]} '+('detail ' * 30)+'</p>'
        for key, title in book["_chapters"]) + '</section><footer>not source</footer>'


def test_sources_are_cached_by_adventure_and_the_catalogue_is_offline(monkeypatch, engine):
    requests = []
    urls = {b["source_url"]: b for b in ADVENTURES.values() if not b["_pages"]}
    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "text/html"}, text=html_for(urls[str(request.url)]))
    real_client = httpx.Client
    monkeypatch.setattr(reader.httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(respond)))
    library = Library(engine)
    for book in urls.values():
        index = read_section(library, "owner-a", book["id"])
        assert "PRIVATE_TEST_SECRET" not in json.dumps(index)
    assert requests == []
    for book in urls.values():
        for key, _ in book["_chapters"]:
            result = read_section(library, "owner-a", book["id"], key)
            assert book["id"] in result["section"]["content"]
            assert result["source_digest"]
    assert len(requests) == len(urls)
    assert len(set(requests)) == len(urls)
    assert library.list("owner-a") == []
    assert CATALOG[0]["adventure_type"] == "original"
    assert not any(c["recommended"] for c in CATALOG)


@pytest.mark.parametrize("response", [
    httpx.Response(200, headers={"content-type": "text/html"}, text="<h1>Sign in</h1>"),
    httpx.Response(302, headers={"location": "http://127.0.0.1/private"}),
    httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"not the article"),
])
def test_changed_sources_and_unapproved_redirects_are_recoverable_errors(monkeypatch, response):
    real_client = httpx.Client
    monkeypatch.setattr(reader.httpx, "Client", lambda **kw: real_client(**kw, transport=httpx.MockTransport(lambda request: response)))
    with pytest.raises(EngineError) as error:
        reader.read_starter("StoryOverview")
    assert error.value.status == 503
    assert "no upload" in str(error.value).lower()
    assert reader.read_starter()["id"] == "frozen-sick"


def blank_pdf(pages=6):
    with pdfium.PdfDocument.new() as document:
        for _ in range(pages):
            page = document.new_page(612, 792); page.close()
        output = BytesIO(); document.save(output); return output.getvalue()


def test_pdf_visual_pages_and_bad_encoding_are_supported_without_gibberish(web, monkeypatch):
    payload = blank_pdf()
    count = []
    def download(book):
        count.append(book["id"]); return payload
    monkeypatch.setattr(reader, "download_source", download)
    assert len(extract_pages(payload)) == 6
    assert needs_visual("\x01\x02\x03 badly encoded")
    args = {"entry_id": "a-wild-sheep-chase", "section_id": "opening"}
    result = tool(web, "read_dnd_adventure", args)
    assert not result.get("isError"), result
    assert len([c for c in result["content"] if c["type"] == "image"]) == 2
    assert "gm_source_images" not in json.dumps(result["structuredContent"])
    page = tool(web, "read_dnd_adventure", {"entry_id": "a-wild-sheep-chase", "page": 3})
    assert not page.get("isError"), page
    assert any(c["type"] == "image" and c["mimeType"] == "image/jpeg" for c in page["content"])
    assert page["structuredContent"]["text"] == "Read the attached source page."
    assert count == ["a-wild-sheep-chase"]
    for invalid in (0, 7, -1):
        assert tool(web, "read_dnd_adventure", {"entry_id": "a-wild-sheep-chase", "page": invalid})["isError"]


def test_batch_reference_fetch_and_model_only_visibility(web, monkeypatch):
    requests = []
    def load(book):
        requests.append(book["id"]); return html_for(book).encode()
    monkeypatch.setattr(reader, "download_source", load)
    result = tool(web, "read_dnd_adventure", {"entry_id": "frozen-sick", "section_ids": ["StoryOverview", "MysteryinPalebankVillage"]})
    assert not result.get("isError"), result
    assert len(result["structuredContent"]["sections"]) == 2 and requests == ["frozen-sick"]
    listing = web.post('/mcp', headers={"Accept": "application/json, text/event-stream"},
                       json={"jsonrpc":"2.0","id":1,"method":"tools/list"}).json()
    reference = next(t for t in listing["result"]["tools"] if t["name"] == "read_dnd_adventure")
    assert reference["_meta"]["ui"]["visibility"] == ["model"]
    assert tool(web, "read_dnd_adventure", {"entry_id": "frozen-sick", "section_ids": ["StoryOverview"]*2})["isError"]


def test_builtin_selection_and_private_ownership_are_validated(engine):
    game = ChatGame(engine)
    state = game.create("owner-a", "Adventure choice", "validate-create", True, "dnd-2024")
    for ref in ({"id":"army-of-the-damned","version":99},
                {"id":"frozen-sick","current_section":"invented"}, {"id":"someone-elses-private-pack"}):
        with pytest.raises(EngineError):
            game.update("owner-a",state["id"],"invalid-reference",1,"Invalid",{"adventure":ref})
        assert engine.get_campaign("owner-a",state["id"]) == state


def test_creation_options_explain_skills_classes_species_and_two_turn_flow(web):
    options = tool(web, "list_dnd_options", {"class_names": ["Fighter"]})
    assert not options.get("isError"), options
    data = options["structuredContent"]
    assert data["creation_flow"]["guided_turns"] == 2
    assert all(c["summary"] and c["starting_features"] for c in data["classes"])
    assert all(s["summary"] for s in data["species"])
    assert all(b["benefits"] for b in data["backgrounds"])
    investigation = next(s for s in data["skills"] if s["name"] == "Investigation")
    assert investigation["usual_ability"] == "INT" and "clues" in investigation["use"]
    assert "Proficiency Bonus" in data["skill_proficiency"]
    guide = tool(web, "read_rules", {"game_id":"dnd-2024","document":"hardener"})["structuredContent"]["content"]
    assert "TWO grouped turns" in guide and "No default adventure" in guide
    assert "Explain every choice visibly" in guide
