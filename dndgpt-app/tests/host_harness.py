"""TEST ONLY: simulated MCP Apps host + real authenticated transport + disposable DB.

Run from dndgpt-app: python -m uvicorn tests.host_harness:app --host 127.0.0.1 --port 8766
Never deploy this module. Its signing key, user, and data are test fixtures.
"""
from contextlib import asynccontextmanager
import json
from pathlib import Path
import tempfile
import time

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
import httpx
import jwt

from app.auth import AuthConfig, JwtVerifier, owner_id
from app.server import create_app
from app.storage import canonical

HERE = Path(__file__).resolve().parent
TEST_ROOT = HERE.parent / ".browser-tmp"
TEST_ROOT.mkdir(exist_ok=True)
TEMP = tempfile.TemporaryDirectory(prefix="fixture-", dir=TEST_ROOT)
CONFIG = AuthConfig("https://fixture-idp.example.test", "https://fixture-idp.example.test/jwks",
                    "http://127.0.0.1:8766/mcp")
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
VERIFIER = JwtVerifier(CONFIG, key_provider=lambda _: KEY.public_key())
TOKEN = jwt.encode({"iss": CONFIG.issuer, "aud": CONFIG.resource_url, "sub": "ui-test-fixture",
                    "exp": int(time.time()) + 7200, "scope": "campaign:read campaign:write"},
                   KEY, algorithm="RS256")
INNER = create_app(Path(TEMP.name) / "fixture.sqlite3", CONFIG, VERIFIER)
OWNER = None
CAMPAIGN_ID = None
AVAILABLE = True


@asynccontextmanager
async def lifespan(app):
    global OWNER, CAMPAIGN_ID
    async with INNER.router.lifespan_context(INNER):
        OWNER = owner_id(await VERIFIER.verify_token(TOKEN))
        engine = INNER.state.engine
        state = engine.create_sandbox(OWNER, "UI test fixture", "browser-create-001")
        CAMPAIGN_ID = state["id"]
        # Deliberately labeled renderer fixtures, never available as player powers.
        state["abilities"] = [{"id": "fixture-bolt", "name": "Fixture Bolt", "rarity": "RARE",
            "activation": "Action", "status": "UNAVAILABLE", "status_reason": "Display fixture only",
            "mp_cost": 4, "simple": "A test card for nested expansion.",
            "mechanics": "Renderer fixture; no executable combat mechanics.",
            "evolutions": [{"id": "fixture-evolution", "name": "Fixture Evolution", "rarity": "EPIC",
                            "mechanics": "Integrated display fixture, not a separate activation."}],
            "imprints": [{"id": "fixture-imprint", "name": "Fixture Imprint", "rarity": "COMMON",
                          "mechanics": "Background-child display fixture."}]}]
        for identity, label, activation, group in (
            ("fixture-guard", "Fixture Guard", "REACTION", None),
            ("fixture-passive", "Fixture Awareness", "PASSIVE", None),
            ("fixture-survey", "Fixture Survey", "Action", "Exploration & Utility")):
            state["abilities"].append({"id": identity, "name": label, "activation": activation,
                "group": group, "rarity": "COMMON", "status": "UNAVAILABLE",
                "status_reason": "Display fixture only", "simple": "Subtab renderer fixture.",
                "mechanics": "Display only; no usable power or campaign acquisition."})
        blade = {"id": "fixture-blade", "name": "Fixture Wayfarer's Blade", "rarity": "RARE",
                 "summary": "Two-handed weapon · display fixture", "weight_kg": 2.4,
                 "description": "An item renderer sample, not acquired campaign equipment.",
                 "stats": {"Attack": "+2 (display fixture)"},
                 "effects": ["No executable item mechanics."], "requirements": "STR 5 (fixture)",
                 "rarity_roll": "PRIVATE_RARITY_RECEIPT_99173"}
        state["equipment"]["Main Hand"] = blade
        state["equipment"]["Off-Hand"] = "fixture-blade"
        state["inventory"] = [blade,
            {"id": "fixture-charm", "name": "Fixture Cartographer's Charm", "rarity": "UNCOMMON",
             "summary": "A keepsake for testing recorded details", "weight_kg": 0.2,
             "description": "A renderer fixture; no campaign acquisition.",
             "charges": {"remaining": 0, "maximum": 3}, "quest_item": True,
             "stats": {"Navigation": "+1 (fixture)", "private_roll": "HIDDEN_NESTED_RECEIPT"}},
            "Uncatalogued fixture keepsake",
            {"id": "fixture-untrusted", "name": "<img src=x onerror=alert('fixture')>",
             "description": "<script>Untrusted fixture text</script>"}]
        state["supplies"] = [{"name": "Fixture trail rations", "quantity": 3, "uses": 3, "bulk": "Light"}]
        with engine.store.transaction() as db:
            state["version"] += 1
            engine._append(db, state, {"kind": "test_fixture_seed", "result": "UI renderer test data only"})
            db.execute("UPDATE campaigns_v1 SET version=?,data=? WHERE id=?",
                       (state["version"], canonical(state), CAMPAIGN_ID))
        yield
    TEMP.cleanup()


app = FastAPI(lifespan=lifespan)


@app.get("/test-host")
def test_host():
    return FileResponse(HERE / "host.html")


@app.get("/test-widget")
def test_widget():
    from app.presentation import dashboard_html
    return HTMLResponse(dashboard_html())


@app.post("/test-rpc")
async def proxy(request: Request):
    if not AVAILABLE:
        return JSONResponse({"error": {"code": -32000, "message": "Connection unavailable (test fixture)"}}, status_code=503)
    body = await request.json()
    if body.get("method") == "tools/call" and body.get("params", {}).get("name") == "render_dashboard":
        body["params"]["arguments"] = {"campaign_id": CAMPAIGN_ID}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=INNER),
                                base_url="http://127.0.0.1:8766") as client:
        response = await client.post("/mcp", json=body, headers={"Authorization": "Bearer " + TOKEN,
                                     "Accept": "application/json, text/event-stream"})
    return response.json()


@app.post("/test-availability")
async def test_availability(request: Request):
    global AVAILABLE
    AVAILABLE = (await request.json())["available"]
    return {"available": AVAILABLE}


@app.get("/test-state")
def test_state():
    engine = INNER.state.engine
    return {"campaign": engine.get_campaign(OWNER, CAMPAIGN_ID),
            "audit": engine.audit(OWNER, CAMPAIGN_ID),
            "preferences": engine.get_view_preferences(OWNER)}


@app.post("/test-proposal")
def test_proposal():
    engine = INNER.state.engine
    state = engine.get_campaign(OWNER, CAMPAIGN_ID)
    return engine.propose_action(OWNER, CAMPAIGN_ID, "browser-resume-001", state["version"], "resume", {})


@app.post("/test-record")
async def test_record(request: Request):
    result = await request.json()
    result["environment"] = "Simulated MCP Apps host in Chromium; disposable test fixtures; not ChatGPT"
    result["verified_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    output = HERE.parent / "test-results/browser.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"saved": True}
