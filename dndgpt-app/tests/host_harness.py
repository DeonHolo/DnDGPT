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
TEMP = tempfile.TemporaryDirectory(prefix="dndgpt-fixture-")
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
SOVEREIGN_ID = None


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
            "range": "10 m", "range_display": "Near · unobstructed target",
            "mechanics_display": "Renderer fixture for a Near target; no executable combat mechanics.",
            "evolutions": [{"id": "fixture-evolution", "name": "Fixture Evolution", "rarity": "EPIC",
                            "mechanics": "Integrated display fixture, not a separate activation.",
                            "private_roll": "HIDDEN_UPGRADE_RECEIPT"}],
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
        state["quest_log"] = [
            {"id": "fixture-crossing", "quest_schema": 1, "name": "Reopen the crossing", "quest_type": "Side quest",
             "finish_condition": "The crossing is passable and the keeper is safe.", "status": "active",
             "objectives": [{"id": "beams", "text": "Clear the fallen beams", "current": 1, "target": 2, "status": "in_progress"},
                            {"id": "keeper", "text": "Bring the keeper to safety", "status": "done"},
                            {"id": "bell", "text": "Recover the bell", "optional": True}],
             "system_reward": {"xp": 50, "currency": {"crowns": 80}, "evolution_credits": 1},
             "contract_payment": {"creditor": "The keeper", "condition": "Return to the lodge", "reward": {"currency": {"crowns": 20}}}},
            {"id": "fixture-finished", "quest_schema": 1, "name": "Light the watchtower", "status": "completed",
             "finish_condition": "The signal fire is lit.", "objectives": [{"id": "fire", "text": "Light the signal fire", "status": "done"}],
             "system_reward": {"xp": 20}, "reward_status": "settled"}]
        state["reward_credits"] = {"earned": 1, "spent": []}
        state["character"].update(ancestry="Stoneborn", ancestry_description="An upright humanlike people with ridged ears and gray, flecked skin. This is a disposable identity fixture.")
        with engine.store.transaction() as db:
            state["version"] += 1
            engine._append(db, state, {"kind": "test_fixture_seed", "result": "UI renderer test data only"})
            db.execute("UPDATE campaigns_v1 SET version=?,data=? WHERE id=?",
                       (state["version"], canonical(state), CAMPAIGN_ID))
        from app.gallery import Gallery
        from app.scenes import SCENES
        import base64
        art = next(scene for scene in SCENES if scene.get("asset"))
        data = (HERE.parent / "app/assets" / art["asset"]).read_bytes()
        Gallery(engine).save(OWNER, CAMPAIGN_ID, "fixture-gallery-seed", "At the woodland crossing",
            caption="Existing dashboard artwork, retained here as a disposable Gallery fixture.", source_kind="upload",
            credit="DnDGPT dashboard artwork fixture; see the project artwork credits.",
            image_data=base64.b64encode(data).decode())
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


@app.get("/test-player-view")
def test_player_view():
    return FileResponse(HERE / "player_view.html")


@app.get("/test-journal-media")
def test_journal_media():
    return FileResponse(HERE / "journal_media.html")


@app.get("/test-sovereign")
def test_sovereign_page():
    return FileResponse(HERE / "sovereign.html")


@app.get("/test-living")
def test_living_page():
    return FileResponse(HERE / "living.html")


@app.post("/test-living-fixture")
def living_fixture():
    from app.chat_game import ChatGame
    from app import records
    from .test_campaign_life import opening, quest
    engine = INNER.state.engine
    game = ChatGame(engine)
    output = {}
    for selected in ("age-of-convergence", "sovereign-system"):
        state = game.create(OWNER, "Living demo · "+selected, "living-fixture-"+selected+"-"+str(time.time_ns()), True, selected)
        with engine.store.transaction() as db:
            raw = engine._get(db, OWNER, state["id"])
            raw.update(phase="adventure", paused=False)
            records.update(db, "campaigns_v1", {"id": raw["id"]}, {"data": canonical(raw)})
        patch = opening()
        if selected == "sovereign-system":
            patch["sovereignty"] = {
                "commanders": [{"id": "own-general", "name": "The returning scout", "abilities": []},
                               {"id": "enemy-general", "name": "PRIVATE_GENERAL", "side": "enemy", "abilities": []}],
                "fronts": [{"id": "secret-front", "name": "PRIVATE_FRONT", "known": False, "objective": "Unrevealed enemy pressure",
                            "target_progress": 2, "status": "active"}],
                "operations": [{"id": "returned", "name": "West road scouts", "commander_id": "own-general", "formation_ids": [],
                                "objective": "Scout the road", "mandate": "Return with observations", "started_at": 0, "due_at": 0,
                                "status": "completed", "outcome": "The scouts returned with a clear-road report."},
                               {"id": "secret-mission", "name": "PRIVATE_OPERATION", "commander_id": "enemy-general", "formation_ids": [],
                                "objective": "Unrevealed mission", "mandate": "Hidden orders", "started_at": 0, "due_at": 60, "status": "active"}]}
        q = quest(); q["objectives"][0]["status"] = "done"
        patch["upsert"]["quest_log"] = [q]
        patch["life_updates"]["places"].append({"id": "bridge", "name": "The restored bridge", "kind": "holding", "description": "A crossing repaired during the quest.", "links": ["quay"]})
        patch["life_updates"]["places"][0]["links"] = ["bridge"]
        patch["life_updates"]["events"] += [
            {"id": "private-plan", "kind": "observation", "subject_id": "captain", "source_id": "encounter", "memory_id": "private", "summary": "PRIVATE_TACTICAL_PLAN", "known_to_player": False},
            {"id": "relationship", "kind": "relationship", "subject_id": "captain", "source_id": "encounter", "stance": "wary", "summary": "The captain accepted a truce after the rescue."},
            {"id": "ferry", "kind": "place_change", "subject_id": "quay", "source_id": "bell", "summary": "The ferry landing reopens.", "controller": "The ferry keeper", "feature": {"id": "ferry", "name": "Working ferry", "description": "Passage to the far bank is available."}},
            {"id": "aftermath", "kind": "quest_aftermath", "subject_id": "quay", "source_id": "bell", "quest_id": "bell", "summary": "The keeper resumes crossings after you return the bell."}]
        state = game.update(OWNER, state["id"], "life-demo-seed", state["version"], "Disposable presentation fixture", patch)["campaign"]
        output[selected] = state
    return output


@app.post("/test-living-record")
async def record_living(request: Request):
    result = await request.json()
    (HERE.parent / "test-results").mkdir(exist_ok=True)
    (HERE.parent / "test-results/living-browser.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"recorded": True}


@app.post("/test-sovereign-draft-fixture")
def sovereign_draft_fixture():
    from app.chat_game import ChatGame
    game = ChatGame(INNER.state.engine)
    state = game.create(OWNER, "Sovereign starting powers · disposable draft", "draft-powers-"+str(time.time_ns()), True, "sovereign-system")
    powers = [{"id": role, "name": "Fixture "+role+" power", "scope": "sovereign", "sovereign_role": role,
               "source": "Class", "rarity": "UNIQUE", "activation": "Passive",
               "mechanics": "A recorded starting-power renderer fixture.", "flavor_text": "The domain answers."}
              for role in ("domain", "general", "army")]
    return game.update(OWNER, state["id"], "draft-power-seed", state["version"], "Record disposable starting-power fixtures", {"upsert": {"abilities": powers}})


@app.post("/test-sovereign-fixture")
def sovereign_fixture():
    global SOVEREIGN_ID
    if SOVEREIGN_ID is not None:
        return {"id": SOVEREIGN_ID}
    from .test_sovereign import fixture_state, milestone
    from app import records
    engine = INNER.state.engine
    prepared = fixture_state(engine)
    SOVEREIGN_ID = prepared["id"]
    with engine.store.transaction() as db:
        state = engine._get(db, "owner-a", SOVEREIGN_ID)
        # Move this disposable fixture to the authenticated browser fixture owner.
        records.update(db, "campaigns_v1", {"id": SOVEREIGN_ID}, {"owner": OWNER})
        state.update(phase="adventure", paused=False, version=2)
        state["character"].update(name="The awakened sovereign", class_name="Wandering Fortress", rarity="UNIQUE")
        state["sovereignty"] = prepared["sovereignty"]
        state["sovereignty"]["domain"]["next_milestone"] = milestone()
        for objective in state["sovereignty"]["domain"]["next_milestone"]["objectives"]:
            objective["status"] = "done"
        power = {"id": "gate", "name": "Open the fortress gate", "rarity": "UNIQUE", "activation": "Active", "scope": "sovereign",
                 "simple": "Deploy a formation through an established gate.",
                 "mechanics_display": "Spend 10 MP and your Action to deploy an assigned formation at an established gate.",
                 "upgrades": [{"id": "gate-two", "name": "Twin arrival", "change_display": "Deploy two formations."}]}
        state["abilities"] = [power, {"id": "blade", "name": "Iron sweep", "rarity": "RARE", "activation": "Active", "scope": "personal",
                                      "simple": "Strike an engaged enemy.", "mechanics_display": "Use your Action for a melee attack."}]
        state["abilities"].extend({"id": "foundation-"+role, "name": "Fortress "+role, "rarity": "UNIQUE",
                                  "scope": "sovereign", "sovereign_role": role, "activation": "Passive",
                                  "mechanics_display": "The permanent "+role+" foundation.",
                                  "upgrades": [{"id": role+"-growth", "name": role.title()+" growth", "change_display": "Gain a standing capability."}]}
                                 for role in ("domain", "general", "army"))
        commander = state["sovereignty"]["commanders"][0]
        commander.update(level=3, xp=20, xp_total=270, description="An autonomous veteran who directs the fortress guard.",
                         abilities=[{**power, "id": "hold", "name": "Hold the line", "scope": "commander"}])
        engine._append(db, state, {"kind": "test_fixture_seed", "result": "Disposable Sovereign UI data"})
        records.update(db, "campaigns_v1", {"id": SOVEREIGN_ID}, {"version": 2, "data": canonical(state)})
    return {"id": SOVEREIGN_ID}


@app.get("/test-sovereign-state")
def sovereign_state():
    return INNER.state.engine.get_campaign(OWNER, SOVEREIGN_ID)


@app.post("/test-sovereign-record")
async def record_sovereign(request: Request):
    result = await request.json()
    result["environment"] = "Local browser, authenticated simulated host and disposable campaigns; not native ChatGPT"
    (HERE.parent / "test-results/sovereign-browser.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"saved": True}


@app.post("/test-journal-record")
async def test_journal_record(request: Request):
    result = await request.json()
    result["environment"] = "Local Chromium host simulator; disposable campaign; not native ChatGPT"
    (HERE.parent / "test-results/journal-media-browser.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {"saved": True}


@app.get("/test-legacy-widget")
def test_legacy_widget():
    """Phone-style bridge only: no standard ui/initialize response is available."""
    from app.presentation import dashboard_html
    shim = """<script>
    window.legacyCalls=[];
    window.openai={displayMode:'inline',widgetState:{},
      callTool:async(name,args)=>{
        window.legacyCalls.push(name);
        const response=await fetch('/test-rpc',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({jsonrpc:'2.0',id:Date.now(),method:'tools/call',params:{name,arguments:args}})});
        const data=await response.json();if(data.error)throw Error(data.error.message);return data.result;
      },setWidgetState:value=>{window.openai.widgetState=value},
      sendFollowUpMessage:async({prompt})=>{window.lastFixturePrompt=prompt;return {}},
      requestDisplayMode:async({mode})=>{window.openai.displayMode=mode;return {mode}}
    };
    </script>"""
    return HTMLResponse(dashboard_html().replace("<head>", "<head>" + shim, 1))


@app.get("/test-approvals")
def test_approvals():
    return FileResponse(HERE / "approvals.html")


@app.get("/test-continuity")
def test_continuity():
    return FileResponse(HERE / "continuity.html")


@app.post("/test-continuity-fixture")
def test_continuity_fixture():
    global CAMPAIGN_ID
    from app.chat_game import ChatGame
    run = str(time.time_ns())
    engine = INNER.state.engine
    game = ChatGame(engine)
    engine.set_view_preferences(OWNER, {"panels": ["character"], "details": [], "hud_hidden": False, "world_tab": "log"})
    state = game.create(OWNER, "Disposable continuity fixture", "create-" + run, True)
    CAMPAIGN_ID = state["id"]
    state = game.update(OWNER, state["id"], "draft-" + run, 1, "Prepared browser fixture", {
        "character": {"name": "Continuity Test Scribe", "class_name": "Test Scribe",
                      "story_summary": "A disposable test character keeps the unfinished repair in view. " * 25},
        "continuity": {"scene": "The test gate", "last_player_intent": "Inspect the gate",
                       "pending_decision": "Speak to the keeper or inspect the hinge?",
                       "unresolved_threads": ["The hinge still needs repair"],
                       "npc_commitments": ["The keeper will return at noon"]},
        "upsert": {"abilities": [{"id": "browser-fixture-ability", "name": "Fixture Survey",
            "activation": "Action", "group": "utility", "rarity": "COMMON", "mp_cost": 3,
            "simple": "Inspect a fixture.", "mechanics": "Display fixture only; not an acquired player power.",
            "upgrades": [{"id": "browser-fixture-upgrade", "name": "Recorded fixture upgrade",
                          "mechanics": "An integrated display fixture; no additional activation."}]}]}})["campaign"]
    state = game.update(OWNER, state["id"], "note-" + run, state["version"], "Recorded test outcome", {
        "continuity": {"last_action": "Inspected the hinge", "outcome": "The pin is bent"}})["campaign"]
    engine.propose_action(OWNER, state["id"], "confirm-" + run, state["version"], "confirm_chat_character", {})
    return {"campaign": state}


@app.post("/test-continuity-record")
async def test_continuity_record(request: Request):
    result = await request.json()
    result["environment"] = "Local Chromium, simulated MCP Apps host, real authenticated transport, disposable SQLite campaigns; not ChatGPT"
    output = HERE.parent / "test-results/continuity-browser.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"saved": True}


@app.post("/test-expire-approval")
async def test_expire_approval(request: Request):
    from app import records
    body = await request.json()
    with INNER.state.engine.store.transaction() as db:
        records.update(db, "proposals_v1", {"id": body["proposal_id"], "owner": OWNER}, {"created_at": time.time() - 901})
    return {"expired": True}


@app.post("/test-approval-record")
async def test_approval_record(request: Request):
    result = await request.json()
    result["environment"] = "Local Chromium, simulated MCP Apps host and disposable campaigns; not ChatGPT"
    output = HERE.parent / "test-results/approvals.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"saved": True}


@app.post("/test-player-record")
async def test_player_record(request: Request):
    result = await request.json()
    result["environment"] = "Local Chromium, disposable renderer fixtures; not ChatGPT"
    output = HERE.parent / "test-results/player-view.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"saved": True}


@app.post("/test-rpc")
async def proxy(request: Request):
    if not AVAILABLE:
        return JSONResponse({"error": {"code": -32000, "message": "Connection unavailable (test fixture)"}}, status_code=503)
    body = await request.json()
    if (body.get("method") == "tools/call" and body.get("params", {}).get("name") == "render_dashboard"
            and not body["params"].get("arguments", {}).get("campaign_id")
            and body["params"].get("arguments", {}).get("game_id", "age-of-convergence") == "age-of-convergence"):
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
