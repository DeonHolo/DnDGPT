"""Official MCP SDK transport and MCP Apps resource registration."""
import hashlib
import json
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import (CallToolResult, ReadResourceRequest, ReadResourceResult,
                       ServerResult, TextContent, TextResourceContents, ToolAnnotations)

from .auth import READ_SCOPE, WRITE_SCOPE, owner_id
from .engine import EngineError
from .version import APP_VERSION
from .standard_rules import rules_guidance
from .presentation import dashboard_html as load_dashboard_html
from .rule_sections import sections as rule_sections, index_text as rule_index
from .gallery import Gallery, GalleryFile
from .game_profiles import AGE, VERSION as GAME_RULES_VERSION, GAMES, game_id as saved_game, rule_source, validate_game

HTML_PATH = Path(__file__).with_name("index.html")
MIME_TYPE = "text/html;profile=mcp-app"
LEGACY_MIME_TYPE = "text/html+skybridge"
RULE_FILES = {"rulebook": "rulebook-v1.0.txt", "hardener": "rule-hardener.txt"}


def rules_page(document, offset, section=None, game_id=AGE):
    if document not in {*RULE_FILES, "index"}:
        raise EngineError(400, "invalid_rules_document", "Choose rulebook, hardener or index")
    try:
        source = rule_source(game_id, "hardener" if document == "hardener" else "rulebook")
    except ValueError as error:
        raise EngineError(422, "invalid_game_rules", str(error))
    text = source["content"]
    source_length = len(text)
    if section is not None:
        if document != "rulebook" or not isinstance(section, str) or section not in rule_sections(text):
            raise EngineError(400, "invalid_rules_section", "Choose a rulebook section from document=index")
        selected = rule_sections(text)[section]
        text = text[selected["start"]:selected["end"]]
    elif document == "index":
        text = rule_index(text)
    if type(offset) is not int or not 0 <= offset <= len(text):
        raise EngineError(400, "invalid_rules_offset", "Offset is outside the document")
    end = min(offset + 8000, len(text))
    if end < len(text):
        boundary = text.rfind("\n", offset, end)
        if boundary > offset:
            end = boundary + 1
    return {"document": document, "offset": offset,
            "next_offset": end if end < len(text) else None, "total_characters": len(text),
            "game_id": game_id, "game_rules_version": GAME_RULES_VERSION,
            "source_sha256": source["source_sha256"], "base_sha256": source["base_sha256"], "section": section,
            "scope": "section" if section is not None else "index" if document == "index" else "document",
            "source_characters": source_length, "content": text[offset:end],
            "standard_play": {**{key: value for key, value in rules_guidance().items() if key in
                                  {"resources", "attributes", "starting_hp", "starting_mp"}}, "game_id": game_id}
                             if offset == 0 and document == "hardener" else {}}


def build_mcp(engine, config, verifier, creation_repository=None):
    html = load_dashboard_html()
    digest = hashlib.sha256(html.encode()).hexdigest()[:12]
    resource_uri = f"ui://dndgpt/dashboard-v1.0-{digest}.html"
    legacy_uri = f"ui://dndgpt/dashboard-compat-{digest}.html"
    creation_html = creation_uri = None
    if creation_repository is not None:
        from .creation_view import html as creation_view
        creation_html = creation_view()
        creation_uri = "ui://dndgpt/creation-v1.0-" + hashlib.sha256(creation_html.encode()).hexdigest()[:12] + ".html"
    parsed = urlsplit(config.resource_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    server = FastMCP(
        "DnDGPT", stateless_http=True, json_response=True,
        token_verifier=verifier if config.configured else None,
        auth=AuthSettings(issuer_url=config.issuer, resource_server_url=config.resource_url,
                          required_scopes=[READ_SCOPE]) if config.configured else None,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[parsed.netloc, "127.0.0.1:*", "localhost:*", "[::1]:*"],
            allowed_origins=[origin]))

    server._mcp_server.version = APP_VERSION

    def metadata(scope=READ_SCOPE, app_only=False):
        scopes = [READ_SCOPE, WRITE_SCOPE] if scope == WRITE_SCOPE else [READ_SCOPE]
        return {"securitySchemes": [{"type": "oauth2", "scopes": scopes}],
                "ui": {"visibility": ["app"] if app_only else ["model", "app"]},
                "openai/widgetAccessible": True}

    def invoke(operation, write=False):
        token = get_access_token()
        if token is None:
            return CallToolResult(isError=True, content=[TextContent(type="text", text="Authentication required")],
                                  _meta={"mcp/www_authenticate": ['Bearer error="invalid_token", error_description="Sign in to DnDGPT", scope="campaign:read"']})
        if write and WRITE_SCOPE not in token.scopes:
            return CallToolResult(isError=True, content=[TextContent(type="text", text="campaign:write required")],
                                  _meta={"mcp/www_authenticate": ['Bearer error="insufficient_scope", error_description="Write permission required", scope="campaign:read campaign:write"']})
        try:
            result = operation(owner_id(token))
            result_meta = result.pop("_meta", {})
            return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
                                  structuredContent=result, _meta=result_meta)
        except EngineError as error:
            return CallToolResult(isError=True, content=[TextContent(type="text", text=str(error))],
                                  structuredContent={"error": error.code, "message": str(error),
                                                     "status": error.status})

    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False,
                            idempotentHint=True)

    from .game_random import GameRandom
    game_random = GameRandom(engine.store, engine.dice, engine)
    from .chat_game import ChatGame
    chat_game = ChatGame(engine)
    gallery = Gallery(engine)
    from .campaign_lifecycle import CampaignLifecycle
    campaign_lifecycle = CampaignLifecycle(engine)
    from .campaign_archive import CampaignArchive
    from .save_history import SaveHistory
    from .continuity import model_view
    archive_service, history = CampaignArchive(engine), SaveHistory(engine)

    def campaign_view(result, view):
        if view != "full":
            result = {**result, "campaign": model_view(result["campaign"], view),
                      "_meta": {**result.get("_meta", {}), "campaign_snapshot": result["campaign"]}}
        return result

    @server.tool(annotations=read, meta=metadata())
    def read_rules(document: Literal["rulebook", "hardener", "index"] = "rulebook",
                   offset: int = 0, section: str | None = None,
                   campaign_id: str | None = None, game_id: str | None = None) -> CallToolResult:
        """Read DnDGPT's current execution checklist, rule index or canonical rules.
        First read document=hardener completely, then document=index. Before a decision,
        fetch relevant rulebook chapters/amendments using a section key from the index.
        Start at offset=0; follow next_offset with the SAME document and section until null.
        Null completes the requested selection, not every rule. Cache by source_sha256;
        refresh after changed hashes, missing context or an explicit rules update.
        Omit section to read the complete document for an audit or offline fallback.
        Player-facing starting kits and summon stats use descriptive reach, not counted
        distance units. Exact spatial mechanics stay private unless explicitly requested.
        A player's explicit custom rulebook takes precedence for that campaign.
        Reading rules never creates a campaign, rolls dice, resumes play or changes saves.
        For an existing campaign pass campaign_id: its saved game selects the book automatically.
        Before creation choose game_id=age-of-convergence or sovereign-system. Do not fetch both.
        Keep campaign_id/game_id with every section/page and cache by game plus source_sha256.
        """
        def read_selected(owner):
            selected = saved_game(engine.get_campaign(owner, campaign_id)) if campaign_id else game_id or AGE
            if campaign_id and game_id is not None and game_id != selected:
                raise EngineError(409, "game_mismatch", "Read the rulebook belonging to this campaign's game")
            return rules_page(document, offset, section, selected)
        return invoke(read_selected)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def create_chat_game(name: str, action_id: str, disposable: bool = False,
                         game_id: Literal["age-of-convergence", "sovereign-system"] = AGE) -> CallToolResult:
        """Create a FRESH chat-led character draft only on explicit new-game/test authorization.
        This does not roll, import, confirm a character, or start an adventure. Use disposable=true
        for tests. ChatGPT follows the complete rulebook and saves its choices through save_chat_update.
        Reuse exact action_id and arguments after uncertain delivery.
        Select the player's requested game; it is fixed for this save. Read that game's rules.
        """
        return invoke(lambda owner: {"campaign": chat_game.create(owner, name, action_id, disposable, game_id),
                                     "game_id": game_id, "standard_play": {**rules_guidance(), "game_id": game_id}}, True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def save_chat_update(campaign_id: str, action_id: str, expected_version: int,
                         summary: str, changes: dict, result_view: Literal["full", "turn"] = "full",
                         begin_adventure: bool = False) -> CallToolResult:
        """Save ONE batched GM update to a fresh chat-led game; ChatGPT adjudicates the rules.
        Use the latest successfully returned version already in context; read again if missing,
        uncertain or conflicted. Use full for story/history; turn only when the needed context is present.
        The successful save already verifies the commit; do not read again just to verify it.
        Character ancestry/ancestry_description retain the chosen race; missing race never means human.
        changes supports partial character (attributes merge), equipment
        Sovereign saves also merge sovereignty and accept sovereign_awards, sovereign_development,
        spend_sovereign_evolution={ability_id,evolution_id}, and sovereign_battle={front_id,phase_id,
        orders:[{id:formation_id,stance:attack|guard|withdraw,target_id?}],phases:1..3}.
        Read sovereign-progression/sovereign-warfare once before using these. Save handles progression,
        real formation rolls and their receipts atomically; never roll each unit separately.
        {slot:inventory_id|null}, name/current_location/opening_preview/notes, fictional_time_seconds,
        level_up_freeze, world (recursive object-field merge), creation/advancement/funds (replace), and collection
        upsert/remove/replace dictionaries.
        Structured quests use quest_schema=1; read rulebook section=quest-journal before creating one.
        Completion/counter progress auto-settles system_reward once; do not also add its XP/funds/items.
        spend_evolution_credit={ability_id,evolution_id} consumes a banked reward with its nested upgrade.
        event_transition={id,eligible:true,context,roll_action_id} records a genuine event receipt;
        use eligible:false with reason for excluded transitions. These belong in the SAME turn save.
        Collections: abilities, conditions, summons, enemies, inventory, supplies, quest_log, world_log,
        generation_ledger. Each record has stable id;
        upsert merges fields by id; remove lists ids; replace explicitly replaces a whole collection.
        Integrated passive Evolutions/Imprints belong inside their existing parent ability, not as
        top-level Passive abilities. Upsert that parent's id with combined mechanics and its complete
        updated evolutions/upgrades/imprints array; preserve prior children because arrays replace.
        Standalone owned passives remain base abilities eligible for Skill Evolution.
        World lists/scalars still replace their values; read full before replacing omitted material.
        An approved correct_chat_state can explicitly replace/delete world details. Never reconstruct
        a world or replace a log from a compact excerpt; preserve facts absent from that view.
        Example: {"character":{"hp":18},"upsert":{"world_log":[{"id":"arrival","text":"Reached the gate"}]}}.
        continuity merges short scene/last_player_intent/last_action/outcome/pending_decision/transition
        text (600 characters each) and unresolved_threads/npc_commitments (at most 8 strings of 240).
        Update it in this SAME save after a meaningful change; never invent a thought or future outcome.
        life_updates optionally saves actors/places, evidence-backed events and player-authorized pacing
        in this same call. Read living-campaigns before first use; no per-turn review/read is required.
        campaign_preferences merges focus=mixed|hunt-explore|conquest and
        dialogue=normal|minimal|on-request. Read campaign-focus once when selecting/changing it;
        keep the saved preference on future turns. A preferences-only save preserves pause/time/build.
        Never set mode/phase/paused/version/authorization. Draft preparation is allowed before play;
        After the player's final Background/attribute/name choices, write character.story_summary,
        starting equipment and opening_preview in this SAME save with changes.begin_adventure=true
        (or top-level begin_adventure=true). The nested form works with older cached tool schemas. This
        completes creation and opens the first scene directly, with no extra confirmation or button.
        Save creation.outfitting.item_ids as the four equipped inventory IDs in allocation order;
        their rarities and actual effects must match the recorded starting-outfit receipt.
        Preserve a player-requested draft/pause. Never infer unchosen build options or opening actions.
        Advancement selections/banking apply immediately; clear level_up_freeze once all pending
        tracks are resolved, then continue already ordered actions without confirmation/resume prompts.
        Gameplay in paused games requires explicit resume or approved correct_chat_state. Reuse EXACT arguments
        and action_id after timeout; never double-apply a reward. A 409 needs a fresh read and review.
        """
        return invoke(lambda owner: campaign_view(chat_game.update(owner, campaign_id, action_id,
                                    expected_version, summary, changes, begin_adventure), result_view), True)

    @server.tool(annotations=read, meta=metadata())
    def get_chat_version(campaign_id: str, version: int) -> CallToolResult:
        """Read an owned historical chat-led save without changing current state. Recover mistakes
        by reviewing propose_action kind=correct_chat_state payload={changes,reason} at CURRENT version.
        History is evidence, never automatic authorization to roll, resume or start an adventure.
        """
        return invoke(lambda owner: chat_game.version(owner, campaign_id, version))

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def roll_game_random(action_id: str, rolls: list[dict],
                         campaign_id: str | None = None) -> CallToolResult:
        """Reusable Python rolls for an explicitly authorized chat-led game or generation request.
        Batch1..20 requests with unique label and kind: dice{sides,count=1,modifier=0},
        check{dc,modifier=0,advantage=false,disadvantage=false}, or rarity{luck:1..20 current score}.
        world_event{context:safe|travel|frontier|unstable,transition_id,pool OR pool_action_id}
        conditionally rolls trigger/category/severity/selection in one request (read rules 32A first).
        Use action_id=event-<campaign_id>-<transition_id>. Precommit the regional pool once;
        reuse its original pool_action_id later. Unchosen candidates stay server-side.
        Reuse EXACT action_id and arguments after a timeout; a retry returns the saved result,
        never rerolls. Do not retry under a new ID to change an outcome. Interpret the results
        in Chat using the complete rulebook. This tool records rolls, not character/game changes.
        It never starts/resumes a campaign or authorizes rolling for a paused/excluded campaign.
        Include campaign_id when this roll belongs to a saved campaign so its receipt is removed
        with that campaign; omit it only for standalone rolls.
        Raw rarity rolls stay hidden by default. No per-roll dashboard confirmation is required.
        For NEW starting equipment, use kind=outfitting with class_rarity equal to the saved class,
        campaign_id set and action_id='starting-outfit-'+campaign_id. One immutable four-item
        budgeted draw per campaign; recover it with get_game_roll rather than drawing again.
        Include slot_preferences=[{slot,weight,basis}]: 1 plausible (default), 2 class OR story fit,
        3 both, 0 genuinely incompatible; justify overrides before rolling. Any legal slot can
        receive the premium item. Equip drawn slots/tiers, weave their origin into Your story,
        and save the receipt under creation.outfitting. Preserve established player history.
        """
        return invoke(lambda owner: game_random.roll(owner, action_id, rolls, campaign_id), True)

    @server.tool(annotations=read, meta=metadata())
    def get_game_roll(action_id: str, show_rolls: bool = False) -> CallToolResult:
        """Recover this account's roll receipt without rolling again. Set show_rolls only on an
        explicit SHOW ROLLS / RARITY AUDIT request; raw rarity details are otherwise hidden.
        """
        return invoke(lambda owner: game_random.get(owner, action_id, show_rolls))

    @server.tool(annotations=read, meta=metadata())
    def list_gallery_images(campaign_id: str, include_removed: bool = False) -> CallToolResult:
        """List saved image titles, captions and credits. Images stay outside gameplay saves.
        Use only for Gallery/image requests; never add a gallery read to routine RPG turns.
        """
        return invoke(lambda owner: gallery.list(owner, campaign_id, include_removed))

    @server.tool(annotations=write, meta={**metadata(WRITE_SCOPE), "openai/fileParams": ["image"]})
    def save_gallery_image(campaign_id: str, action_id: str, title: str, image: GalleryFile,
                           caption: str = "", source_kind: Literal["generated", "upload"] = "generated",
                           source_url: str = "", credit: str = "", scene_ref: str = "") -> CallToolResult:
        """Save a generated or uploaded ChatGPT image file to the campaign Gallery with a label.
        Pass the actual available file through image; generate art only when the player requests it.
        Reuse action_id on retry. Retains a private image copy; never changes gameplay or time.
        If the host cannot expose a generated image as a file, offer Gallery's Upload/Choose files.
        """
        return invoke(lambda owner: gallery.save(owner, campaign_id, action_id, title, caption,
                      source_kind, source_url, credit, scene_ref, file=image), True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def save_gallery_url(campaign_id: str, action_id: str, title: str, image_url: str,
                         caption: str = "", source_url: str = "", credit: str = "",
                         scene_ref: str = "", auto_curated: bool = False) -> CallToolResult:
        """Save a public image URL to the private campaign Gallery, with title/caption/source credit.
        When web images were already SHOWN for a scene/world overview, retain 1..3 representative
        images with auto_curated=true and the same established scene_ref. Deduplicates image copies.
        Save selected images, not every search result. Never claim inaccessible images were saved.
        Use source_url for the credit page. Image-only action: no mechanics, rolls or fictional time.
        """
        return invoke(lambda owner: gallery.save(owner, campaign_id, action_id, title, caption,
                      "web", source_url, credit, scene_ref, auto_curated, image_url=image_url), True)

    @server.tool(annotations=read, meta=metadata(app_only=True))
    def get_gallery_image(campaign_id: str, image_id: str,
                          size: Literal["thumbnail", "full"] = "thumbnail") -> CallToolResult:
        """Load an owned gallery image into the widget. Image bytes are widget-only metadata."""
        return invoke(lambda owner: gallery.image(owner, campaign_id, image_id, size))

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE, app_only=True))
    def upload_gallery_image(campaign_id: str, action_id: str, title: str, image_data: str,
                             caption: str = "") -> CallToolResult:
        """Widget upload fallback. Store a selected image without changing gameplay."""
        return invoke(lambda owner: gallery.save(owner, campaign_id, action_id, title, caption,
                      "upload", image_data=image_data), True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE, app_only=True))
    def set_gallery_image_removed(campaign_id: str, image_id: str, removed: bool) -> CallToolResult:
        """Reversibly hide or restore a Gallery entry; no gameplay change."""
        return invoke(lambda owner: gallery.visibility(owner, campaign_id, image_id, removed), True)

    if creation_repository is not None:
        from .creation_tools import register_creation_tools
        register_creation_tools(server, creation_repository, invoke, metadata, read, write, creation_uri)

    @server.tool(annotations=read, meta=metadata())
    def list_campaigns(game_id: Literal["age-of-convergence", "sovereign-system"] = AGE) -> CallToolResult:
        """List this authenticated account's stored sandboxes. Does not start or resume a game."""
        return invoke(lambda owner: {"game_id": game_id, "games": list(GAMES), "campaigns": engine.list_campaigns(owner, game_id)})

    preview_write = ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                    idempotentHint=False, openWorldHint=False)

    @server.tool(annotations=preview_write, meta=metadata(WRITE_SCOPE))
    def preview_delete_campaign(campaign_id: str, expected_version: int) -> CallToolResult:
        """Prepare a permanent deletion preview for one owned campaign. This does not delete it.
        Read the current campaign first, then show its exact name and removal/retention scope to
        the user. Wait for their explicit approval before calling delete_campaign. The returned
        one-time confirmation_token expires after 15 minutes.
        """
        return invoke(lambda owner: campaign_lifecycle.preview_delete(owner, campaign_id,
                                                                       expected_version), True)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                 idempotentHint=True, openWorldHint=False), meta=metadata(WRITE_SCOPE))
    def delete_campaign(campaign_id: str, expected_version: int, confirmation_token: str,
                        confirm_permanent: bool) -> CallToolResult:
        """Permanently delete exactly one campaign after explicit user approval.
        Do not call until the user has seen the preview and explicitly approved permanent deletion.
        Cleanup is bounded; if cleanup_pending is true, retry with the exact same arguments until
        deleted is true. The campaign will disappear from listings as soon as deletion starts.
        """
        return invoke(lambda owner: campaign_lifecycle.delete(
            owner, campaign_id, expected_version, confirmation_token, confirm_permanent), True)

    @server.tool(annotations=read, meta=metadata())
    def get_campaign(campaign_id: str, view: Literal["full", "turn", "resume"] = "full") -> CallToolResult:
        """Read committed state without mutation, time advancement or raw rarity rolls.
        Use full for story/history decisions unless the relevant saved context is already present.
        turn retains current mechanics but omits old logs/world articles; it is not complete memory.
        Before relying on an omitted promise, past event or world detail, retrieve full. If no record
        exists, report uncertainty; never treat omission as proof that something never happened.
        view=resume supplies a compact continuity brief for a fresh chat; inspect full details only as needed.
        A brief read never authorizes continuing, rolling or resuming. Missing continuity is marked, not invented.
        Reuse the latest successful read/save in the current context; no obligatory read before every save.
        Plan authorized rounds/choices from the actual equipped effects and upgraded skills in that state;
        respect triggers, charges, cooldowns and action costs, counting derived passive bonuses once.
        """
        return invoke(lambda owner: campaign_view(engine.campaign_context(owner, campaign_id), view))

    @server.tool(annotations=read, meta=metadata())
    def list_chat_versions(campaign_id: str, before: int | None = None, limit: int = 20) -> CallToolResult:
        """Read a bounded page of owned save summaries only on a history/recovery request, never every turn."""
        return invoke(lambda owner: history.list(owner, campaign_id, before, limit))

    @server.tool(annotations=read, meta=metadata(app_only=True))
    def compare_chat_version(campaign_id: str, version: int) -> CallToolResult:
        """APP ONLY. Show public changes from the preceding saved version without loading it as current state."""
        return invoke(lambda owner: history.compare(owner, campaign_id, version))

    @server.tool(annotations=read, meta=metadata(app_only=True))
    def export_campaign(campaign_id: str) -> CallToolResult:
        """APP ONLY. Download this owned campaign's private portable current snapshot, without changing it."""
        return invoke(lambda owner: archive_service.export(owner, campaign_id))

    @server.tool(annotations=read, meta=metadata(app_only=True))
    def preview_campaign_import(archive: dict) -> CallToolResult:
        """APP ONLY. Validate a player-selected portable export and show its restore scope; creates nothing."""
        return invoke(lambda owner: archive_service.preview(archive))

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE, app_only=True))
    def import_campaign(archive: dict, action_id: str, confirm_restore: bool) -> CallToolResult:
        """APP ONLY. After the player reviews and confirms, restore a separate PAUSED campaign.
        Never overwrite an existing campaign or start/resume play. Retry EXACT arguments/action_id.
        """
        return invoke(lambda owner: archive_service.restore(owner, archive, action_id, confirm_restore), True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def create_sandbox(name: str, action_id: str) -> CallToolResult:
        """Only on explicit development/test request, create a new empty PAUSED sandbox. Not character creation."""
        return invoke(lambda owner: {"campaign": engine.create_sandbox(owner, name, action_id)}, True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def propose_action(campaign_id: str, action_id: str, expected_version: int,
                       kind: str, payload: dict) -> CallToolResult:
        """Preview a manual pause{}, resume{} or correct_chat_state{changes,reason} for app approval.
        Creation completes through save_chat_update(changes={begin_adventure:true}), without an approval.
        Retired creation kinds return a direct-save handoff, never an approval proposal or a commit.
        Advancement choices apply through save_chat_update and resume automatically when resolved.
        Routine chat-led turns use save_chat_update without per-turn approval. Legacy engine commands
        remain sandbox-only. Present the exact proposal for user approval in render_dashboard.
        """
        def propose(owner):
            if kind in {"confirm_chat_character", "start_chat_adventure"}:
                state = engine.get_campaign(owner, campaign_id)
                if state.get("mode") != "chat" or payload:
                    raise EngineError(422, "invalid_creation_handoff", "Use an owned chat-led draft and an empty payload")
                if state["version"] != expected_version:
                    raise EngineError(409, "version_conflict", f"Current version is {state['version']}; read before saving again")
                if state["phase"] == "adventure":
                    return {"status": "paused" if state["paused"] else "already_active",
                            "campaign_id": campaign_id, "version": state["version"], "approval_required": False}
                return {"status": "direct_creation_save_required", "approval_required": False,
                        "committed": False,
                        "message": "Complete actual player choices, story and equipment, then save once through chat. "
                                   "Use the saved opening; no confirmation button or repeat player acceptance is needed.",
                        "next_action": {"tool": "save_chat_update", "arguments": {
                            "campaign_id": campaign_id, "action_id": action_id,
                            "expected_version": expected_version,
                            "summary": "Complete the chosen character and open the saved first scene",
                            "changes": {"begin_adventure": True}}}}
            return engine.propose_action(owner, campaign_id, action_id, expected_version, kind, payload)
        return invoke(propose, True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def roll_dice(campaign_id: str, action_id: str, expected_version: int,
                  sides: int, count: int = 1) -> CallToolResult:
        """Propose auditable dice for an explicitly requested sandbox test; rolls only AFTER app approval."""
        return invoke(lambda owner: engine.propose_action(owner, campaign_id, action_id,
                       expected_version, "roll_dice", {"sides": sides, "count": count}), True)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True,
                 idempotentHint=True, openWorldHint=False), meta=metadata(WRITE_SCOPE, app_only=True))
    def execute_confirmed_action(proposal_id: str, approval_token: str) -> CallToolResult:
        """APP ONLY. Commit exactly the preview approved by the user. Token is widget-only metadata.
        Retry the same proposal/token after transport failure; never create a replacement action to retry.
        """
        return invoke(lambda owner: engine.execute_confirmed_action(owner, proposal_id, approval_token), True)

    @server.tool(annotations=read, meta=metadata())
    def audit(campaign_id: str, show_rolls: bool = False) -> CallToolResult:
        """Read event-chain integrity. Include raw rarity rolls only after an explicit SHOW ROLLS / RARITY AUDIT request."""
        return invoke(lambda owner: engine.audit(owner, campaign_id, show_rolls))

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE, app_only=True))
    def set_view_preferences(preferences: dict) -> CallToolResult:
        """APP ONLY. Store panel/view preferences. Never changes campaign state, rolls, or clocks."""
        return invoke(lambda owner: engine.set_view_preferences(owner, preferences), True)

    render_meta = metadata()
    render_meta["ui"]["resourceUri"] = resource_uri
    render_meta["openai/outputTemplate"] = legacy_uri
    render_meta["openai/ui"] = {"entrypoints": [{"type": "thread"}, {"type": "global"}]}

    @server.tool(title="Campaign dashboard", annotations=read, meta=render_meta)
    def render_dashboard(campaign_id: str | None = None,
                         game_id: Literal["age-of-convergence", "sovereign-system"] | None = None) -> CallToolResult:
        """Use when the player asks to open/show the campaign dashboard on desktop or mobile.
        Call again when it is closed, missing or outdated, even for the same campaign.
        get_campaign refreshes saved data but cannot open an absent UI. Return this component.
        Includes core chapters, Gallery and the selected game's panels. Read-only: never starts play.
        Once visibly mounted, normal saves/data calls update it without routine per-turn renders.
        """
        return invoke(lambda owner: engine.dashboard(owner, campaign_id, game_id))

    ui_meta = {"ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}},
               "openai/ui": {"availableDisplayModes": ["inline", "fullscreen", "pip"],
                             "preferredDisplayMode": "inline"},
               "openai/widgetDescription": "Seven core RPG chapters plus a saved-image Gallery; action choices send chat follow-ups.",
               "openai/widgetPrefersBorder": True,
               "openai/widgetCSP": {"connect_domains": [], "resource_domains": []}}

    @server.resource(resource_uri, mime_type=MIME_TYPE, meta=ui_meta)
    def dashboard_html() -> str:
        return html

    @server.resource(legacy_uri, mime_type=LEGACY_MIME_TYPE, meta=ui_meta)
    def dashboard_compatibility_html() -> str:
        return html

    resources = {resource_uri: (html, ui_meta, MIME_TYPE),
                 legacy_uri: (html, ui_meta, LEGACY_MIME_TYPE)}
    if creation_uri is not None:
        creation_meta = {**ui_meta, "openai/widgetDescription":
                         "Saved character choices, full source details and separate character/adventure approvals. Development preview."}
        resources[creation_uri] = (creation_html, creation_meta, MIME_TYPE)

        @server.resource(creation_uri, mime_type=MIME_TYPE, meta=creation_meta)
        def creation_resource() -> str:
            return creation_html

    # FastMCP 1.29's string-resource adapter drops content-level _meta. Register
    # the SDK's ReadResourceResult directly so hosts receive the actual CSP.
    async def read_resource(request):
        uri = str(request.params.uri)
        if uri in resources:
            content, content_meta, mime_type = resources[uri]
        elif re.fullmatch(r"ui://dndgpt/dashboard-(?:v1\.0|compat)-[0-9a-f]{12}\.html", uri):
            # A cached tool catalog may still reference a previous deployment's hash.
            content, content_meta = html, ui_meta
            mime_type = LEGACY_MIME_TYPE if "/dashboard-compat-" in uri else MIME_TYPE
        else:
            raise ValueError("Unknown UI resource")
        return ServerResult(ReadResourceResult(contents=[TextResourceContents(
            uri=uri, mimeType=mime_type, text=content, _meta=content_meta)]))

    server._mcp_server.request_handlers[ReadResourceRequest] = read_resource

    @server._mcp_server.list_tools()
    async def list_tools_with_security():
        tools = await server.list_tools()
        for tool in tools:
            tool.securitySchemes = tool.meta["securitySchemes"]
        return tools

    return server, resource_uri
