"""Official MCP SDK transport and MCP Apps resource registration."""
import hashlib
import json
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

HTML_PATH = Path(__file__).with_name("index.html")
MIME_TYPE = "text/html;profile=mcp-app"
RULE_FILES = {"rulebook": "rulebook-v1.0.txt", "hardener": "rule-hardener.txt"}


def rules_page(document, offset):
    if document not in RULE_FILES:
        raise EngineError(400, "invalid_rules_document", "Choose rulebook or hardener")
    data = (HTML_PATH.parent.parent / "rules" / RULE_FILES[document]).read_bytes()
    text = data.decode("utf-8")
    if type(offset) is not int or not 0 <= offset <= len(text):
        raise EngineError(400, "invalid_rules_offset", "Offset is outside the document")
    end = min(offset + 8000, len(text))
    if end < len(text):
        boundary = text.rfind("\n", offset, end)
        if boundary > offset:
            end = boundary + 1
    return {"document": document, "offset": offset,
            "next_offset": end if end < len(text) else None, "total_characters": len(text),
            "source_sha256": hashlib.sha256(data).hexdigest(), "content": text[offset:end],
            "standard_play": rules_guidance()}


def build_mcp(engine, config, verifier, creation_repository=None):
    html = load_dashboard_html()
    digest = hashlib.sha256(html.encode()).hexdigest()[:12]
    resource_uri = f"ui://dndgpt/dashboard-v1.0-{digest}.html"
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
    from .campaign_lifecycle import CampaignLifecycle
    campaign_lifecycle = CampaignLifecycle(engine)

    @server.tool(annotations=read, meta=metadata())
    def read_rules(document: Literal["rulebook", "hardener"] = "rulebook",
                   offset: int = 0) -> CallToolResult:
        """Read the standard DnDGPT rulebook or Rule Hardener from the hosted service.
        No file upload is needed for standard rules. Start each document at offset=0;
        next_offset identifies its next page, or is null when the complete document is read.
        Read both complete documents before standard character generation or adjudication.
        Player-facing starting kits and summon stats use descriptive reach, not counted
        distance units. Exact spatial mechanics stay private unless explicitly requested.
        A player's explicit custom rulebook takes precedence for that campaign.
        Reading rules never creates a campaign, rolls dice, resumes play or changes saves.
        """
        return invoke(lambda owner: rules_page(document, offset))

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def create_chat_game(name: str, action_id: str, disposable: bool = False) -> CallToolResult:
        """Create a FRESH chat-led character draft only on explicit new-game/test authorization.
        This does not roll, import, confirm a character, or start an adventure. Use disposable=true
        for tests. ChatGPT follows the complete rulebook and saves its choices through save_chat_update.
        Reuse exact action_id and arguments after uncertain delivery.
        """
        return invoke(lambda owner: {"campaign": chat_game.create(owner, name, action_id, disposable),
                                     "standard_play": rules_guidance()}, True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def save_chat_update(campaign_id: str, action_id: str, expected_version: int,
                         summary: str, changes: dict) -> CallToolResult:
        """Save ONE batched GM update to a fresh chat-led game; ChatGPT adjudicates the rules.
        Read current version first. changes supports partial character (attributes merge), equipment
        {slot:inventory_id|null}, name/current_location/opening_preview/notes, fictional_time_seconds,
        level_up_freeze, world/creation/advancement/funds objects (each replaces that object), and collection
        upsert/remove/replace dictionaries. Collections: abilities, conditions, summons, enemies,
        inventory, supplies, quest_log, world_log, generation_ledger. Each record has stable id;
        upsert merges fields by id; remove lists ids; replace explicitly replaces a whole collection.
        Example: {"character":{"hp":18},"upsert":{"world_log":[{"id":"arrival","text":"Reached the gate"}]}}.
        Never set mode/phase/paused/version/authorization. Draft preparation is allowed before play;
        confirm_chat_character and start_chat_adventure are separate propose_action/app approvals.
        Paused games require explicit resume or approved correct_chat_state. Reuse EXACT arguments
        and action_id after timeout; never double-apply a reward. A 409 needs a fresh read and review.
        """
        return invoke(lambda owner: chat_game.update(owner, campaign_id, action_id,
                      expected_version, summary, changes), True)

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
        Reuse EXACT action_id and arguments after a timeout; a retry returns the saved result,
        never rerolls. Do not retry under a new ID to change an outcome. Interpret the results
        in Chat using the complete rulebook. This tool records rolls, not character/game changes.
        It never starts/resumes a campaign or authorizes rolling for a paused/excluded campaign.
        Include campaign_id when this roll belongs to a saved campaign so its receipt is removed
        with that campaign; omit it only for standalone rolls.
        Raw rarity rolls stay hidden by default. No per-roll dashboard confirmation is required.
        """
        return invoke(lambda owner: game_random.roll(owner, action_id, rolls, campaign_id), True)

    @server.tool(annotations=read, meta=metadata())
    def get_game_roll(action_id: str, show_rolls: bool = False) -> CallToolResult:
        """Recover this account's roll receipt without rolling again. Set show_rolls only on an
        explicit SHOW ROLLS / RARITY AUDIT request; raw rarity details are otherwise hidden.
        """
        return invoke(lambda owner: game_random.get(owner, action_id, show_rolls))

    if creation_repository is not None:
        from .creation_tools import register_creation_tools
        register_creation_tools(server, creation_repository, invoke, metadata, read, write, creation_uri)

    @server.tool(annotations=read, meta=metadata())
    def list_campaigns() -> CallToolResult:
        """List this authenticated account's stored sandboxes. Does not start or resume a game."""
        return invoke(lambda owner: {"campaigns": engine.list_campaigns(owner)})

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
    def get_campaign(campaign_id: str) -> CallToolResult:
        """Read authoritative current state without raw rarity rolls, time advancement, or mutation."""
        return invoke(lambda owner: {"campaign": engine.get_campaign(owner, campaign_id),
                                      "_meta": engine.pending_approval(owner, campaign_id)})

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def create_sandbox(name: str, action_id: str) -> CallToolResult:
        """Only on explicit development/test request, create a new empty PAUSED sandbox. Not character creation."""
        return invoke(lambda owner: {"campaign": engine.create_sandbox(owner, name, action_id)}, True)

    @server.tool(annotations=write, meta=metadata(WRITE_SCOPE))
    def propose_action(campaign_id: str, action_id: str, expected_version: int,
                       kind: str, payload: dict) -> CallToolResult:
        """Preview an app-confirmed action without committing. Chat-led games support
        confirm_chat_character{}, start_chat_adventure{} (after an opening_preview), pause{}, resume{},
        and correct_chat_state{changes,reason}. Confirming a character never starts an adventure.
        Routine chat-led turns use save_chat_update without per-turn approval. Legacy engine commands
        remain sandbox-only. Present the exact proposal for user approval in render_dashboard.
        """
        return invoke(lambda owner: engine.propose_action(owner, campaign_id, action_id,
                                                          expected_version, kind, payload), True)

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
    render_meta["openai/outputTemplate"] = resource_uri
    render_meta["openai/ui"] = {"entrypoints": [{"type": "thread"}]}

    @server.tool(title="Campaign dashboard", annotations=read, meta=render_meta)
    def render_dashboard(campaign_id: str | None = None) -> CallToolResult:
        """Render the seven-panel HUD from stored state. Does not create, roll, or resume anything.
        Use data tools for mutations; keep this view mounted and refresh it through get_campaign.
        """
        return invoke(lambda owner: engine.dashboard(owner, campaign_id))

    ui_meta = {"ui": {"prefersBorder": True, "csp": {"connectDomains": [], "resourceDomains": []}},
               "openai/ui": {"availableDisplayModes": ["inline", "fullscreen"],
                             "preferredDisplayMode": "fullscreen"},
               "openai/widgetDescription": "Seven RPG chapters with navigation summaries; action choices send chat follow-ups.",
               "openai/widgetPrefersBorder": True,
               "openai/widgetCSP": {"connect_domains": [], "resource_domains": []}}

    @server.resource(resource_uri, mime_type=MIME_TYPE, meta=ui_meta)
    def dashboard_html() -> str:
        return html

    resources = {resource_uri: (html, ui_meta)}
    if creation_uri is not None:
        creation_meta = {**ui_meta, "openai/widgetDescription":
                         "Saved character choices, full source details and separate character/adventure approvals. Development preview."}
        resources[creation_uri] = (creation_html, creation_meta)

        @server.resource(creation_uri, mime_type=MIME_TYPE, meta=creation_meta)
        def creation_resource() -> str:
            return creation_html

    # FastMCP 1.29's string-resource adapter drops content-level _meta. Register
    # the SDK's ReadResourceResult directly so hosts receive the actual CSP.
    async def read_resource(request):
        uri = str(request.params.uri)
        if uri not in resources:
            raise ValueError("Unknown UI resource")
        content, content_meta = resources[uri]
        return ServerResult(ReadResourceResult(contents=[TextResourceContents(
            uri=uri, mimeType=MIME_TYPE, text=content, _meta=content_meta)]))

    server._mcp_server.request_handlers[ReadResourceRequest] = read_resource

    @server._mcp_server.list_tools()
    async def list_tools_with_security():
        tools = await server.list_tools()
        for tool in tools:
            tool.securitySchemes = tool.meta["securitySchemes"]
        return tools

    return server, resource_uri
