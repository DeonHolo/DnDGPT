"""FastAPI adapter plus the authenticated MCP Apps endpoint."""
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from .auth import AuthConfig, JwtVerifier, READ_SCOPE, WRITE_SCOPE, owner_id
from .engine import Engine, EngineError
from .mcp_server import build_mcp
from .storage import Store
from .version import APP_VERSION, RULES_VERSION

HERE = Path(__file__).resolve().parent


class CreateSandbox(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str = Field(min_length=1, max_length=80)
    action_id: str = Field(min_length=8, max_length=128)


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action_id: str = Field(min_length=8, max_length=128)
    expected_version: StrictInt = Field(ge=1)
    kind: str
    payload: dict = Field(default_factory=dict)


class CreateChatGame(CreateSandbox):
    disposable: bool = False


class ChatUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action_id: str = Field(min_length=8, max_length=128)
    expected_version: StrictInt = Field(ge=1)
    summary: str = Field(min_length=1, max_length=2000)
    changes: dict
    begin_adventure: bool = False


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    approval_token: str = Field(min_length=1, max_length=256)


class ImportPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    archive: dict


class ImportCampaign(ImportPreview):
    action_id: str = Field(min_length=8, max_length=128)
    confirm_restore: bool


class CreationStart(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    world_preview: str = Field(min_length=1, max_length=20000)
    action_id: str = Field(min_length=8, max_length=128)


def create_app(db_path=None, auth_config=None, token_verifier=None, *, enable_creation_drafts=False,
               enable_combat=False, store=None):
    if type(enable_creation_drafts) is not bool:
        raise ValueError("enable_creation_drafts must be boolean")
    config = auth_config or AuthConfig.from_env()
    config.validate()
    if store is not None and (db_path is not None or enable_creation_drafts):
        raise ValueError("Hosted persistence cannot use a SQLite path or the optional creation adapter")
    store = store if store is not None else Store(db_path or os.getenv("DNDGPT_DB", HERE.parent / "data/campaigns.sqlite3"))
    engine = Engine(store, enable_combat=enable_combat)
    from .chat_game import ChatGame
    chat_game = ChatGame(engine)
    from .campaign_archive import CampaignArchive
    from .save_history import SaveHistory
    from .continuity import model_view
    archive_service, history = CampaignArchive(engine), SaveHistory(engine)
    verifier = token_verifier or JwtVerifier(config)
    creation_repository = None
    if enable_creation_drafts:
        from .creation_repository import CreationRepository
        creation_repository = CreationRepository(store)
    mcp, resource_uri = build_mcp(engine, config, verifier, creation_repository)
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title="DnDGPT", version=APP_VERSION, lifespan=lifespan)
    app.state.engine, app.state.mcp, app.state.resource_uri = engine, mcp, resource_uri
    app.state.auth_config = config
    app.state.creation_repository = creation_repository

    @app.exception_handler(EngineError)
    async def engine_error(request, error):
        return JSONResponse(status_code=error.status,
                            content={"code": error.code, "detail": str(error)})

    @app.middleware("http")
    async def secure_response(request, call_next):
        if request.url.path.startswith("/mcp") and not config.configured:
            return JSONResponse(status_code=503, content={"detail": "OAuth is not configured"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    async def authenticated(request: Request):
        if not config.configured:
            raise HTTPException(503, "OAuth is not configured")
        challenge = ('Bearer resource_metadata="' +
                     config.resource_url.removesuffix("/mcp") +
                     '/.well-known/oauth-protected-resource/mcp"')
        authorization = request.headers.get("authorization", "")
        scheme, _, raw = authorization.partition(" ")
        token = await verifier.verify_token(raw) if scheme.lower() == "bearer" and raw else None
        if token is None:
            raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": challenge})
        if READ_SCOPE not in token.scopes:
            raise HTTPException(403, "campaign:read required",
                                headers={"WWW-Authenticate": challenge + ', error="insufficient_scope"'})
        return token

    async def writable(token=Depends(authenticated)):
        if WRITE_SCOPE not in token.scopes:
            raise HTTPException(403, "campaign:write required",
                                headers={"WWW-Authenticate": 'Bearer error="insufficient_scope", scope="campaign:write"'})
        return token

    @app.get("/")
    def index():
        from .presentation import dashboard_html
        return HTMLResponse(dashboard_html())

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": APP_VERSION, "rules_version": RULES_VERSION,
                "engine": "incremental sandbox", "persistent_db": True,
                "oauth_configured": config.configured, "chatgpt_integration": False,
                "live_client_verification": "pending", "model_api_calls": False,
                "creation_drafts_enabled": enable_creation_drafts, "sandbox_combat_enabled": enable_combat,
                "character_creation": False, "chat_led_saved_state": True,
                "gm_adjudication": "ChatGPT"}

    @app.get("/.well-known/oauth-protected-resource")
    @app.get("/.well-known/oauth-protected-resource/mcp")
    def protected_resource():
        if not config.configured:
            raise HTTPException(503, "OAuth is not configured")
        return {"resource": config.resource_url, "authorization_servers": [config.issuer],
                "scopes_supported": [READ_SCOPE, WRITE_SCOPE],
                "bearer_methods_supported": ["header"], "resource_name": "DnDGPT"}

    @app.get("/api/campaigns")
    def list_campaigns(token=Depends(authenticated)):
        return {"campaigns": engine.list_campaigns(owner_id(token))}

    @app.post("/api/campaigns")
    def create_campaign(spec: CreateSandbox, token=Depends(writable)):
        return {"campaign": engine.create_sandbox(owner_id(token), spec.name, spec.action_id)}

    @app.get("/api/campaigns/{campaign_id}")
    def campaign(campaign_id: str, token=Depends(authenticated)):
        return {"campaign": engine.get_campaign(owner_id(token), campaign_id)}

    @app.post("/api/chat-games")
    def create_chat_game(spec: CreateChatGame, token=Depends(writable)):
        return {"campaign": chat_game.create(owner_id(token), **spec.model_dump())}

    @app.post("/api/campaigns/{campaign_id}/chat-updates")
    def save_chat_update(campaign_id: str, spec: ChatUpdate, token=Depends(writable)):
        return chat_game.update(owner_id(token), campaign_id, **spec.model_dump())

    @app.get("/api/campaigns/{campaign_id}/versions/{version}")
    def chat_version(campaign_id: str, version: int, token=Depends(authenticated)):
        return chat_game.version(owner_id(token), campaign_id, version)

    @app.get("/api/campaigns/{campaign_id}/versions")
    def chat_history(campaign_id: str, before: int | None = None, limit: int = 20, token=Depends(authenticated)):
        return history.list(owner_id(token), campaign_id, before, limit)

    @app.get("/api/campaigns/{campaign_id}/versions/{version}/changes")
    def version_changes(campaign_id: str, version: int, token=Depends(authenticated)):
        return history.compare(owner_id(token), campaign_id, version)

    @app.get("/api/campaigns/{campaign_id}/resume")
    def resume_brief(campaign_id: str, token=Depends(authenticated)):
        return model_view(engine.get_campaign(owner_id(token), campaign_id), "resume")

    @app.get("/api/campaigns/{campaign_id}/export")
    def export_campaign(campaign_id: str, token=Depends(authenticated)):
        return archive_service.export(owner_id(token), campaign_id)

    @app.post("/api/imports/preview")
    def preview_import(spec: ImportPreview, token=Depends(authenticated)):
        return archive_service.preview(spec.archive)

    @app.post("/api/imports")
    def import_campaign(spec: ImportCampaign, token=Depends(writable)):
        return archive_service.restore(owner_id(token), **spec.model_dump())

    @app.get("/api/campaigns/{campaign_id}/events")
    def events(campaign_id: str, show_rolls: bool = False, token=Depends(authenticated)):
        return engine.audit(owner_id(token), campaign_id, show_rolls)

    @app.post("/api/campaigns/{campaign_id}/proposals")
    def propose(campaign_id: str, spec: Proposal, token=Depends(writable)):
        return engine.propose_action(owner_id(token), campaign_id, **spec.model_dump())

    @app.post("/api/proposals/{proposal_id}/confirm")
    def confirm(proposal_id: str, spec: Confirmation, token=Depends(writable)):
        return engine.execute_confirmed_action(owner_id(token), proposal_id, spec.approval_token)

    if creation_repository is not None:
        @app.get("/api/creation-drafts")
        def list_drafts(token=Depends(authenticated)):
            return creation_repository.list_drafts(owner_id(token))

        @app.post("/api/creation-drafts")
        def propose_creation_start(spec: CreationStart, token=Depends(writable)):
            return creation_repository.propose_start(owner_id(token), **spec.model_dump())

        @app.get("/api/creation-drafts/{draft_id}")
        def creation_draft(draft_id: str, include_preparation: bool = False,
                           token=Depends(authenticated)):
            return creation_repository.get_draft(owner_id(token), draft_id, include_preparation)

        @app.post("/api/creation-drafts/{draft_id}/proposals")
        def propose_creation_transition(draft_id: str, spec: Proposal, token=Depends(writable)):
            return creation_repository.propose_transition(owner_id(token), draft_id, **spec.model_dump())

        @app.get("/api/creation-drafts/{draft_id}/events")
        def creation_audit(draft_id: str, show_rolls: bool = False, token=Depends(authenticated)):
            return creation_repository.audit(owner_id(token), draft_id, show_rolls)

    app.mount("/", mcp_app)
    return app


app = create_app()
