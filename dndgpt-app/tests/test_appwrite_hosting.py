"""Hosted contracts against an explicit transactional Appwrite test double."""
import asyncio
import copy
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from app import records
from app.appwrite_entry import dispatch, main
from app.appwrite_store import AppwriteAPI, AppwriteStore
from app.chat_game import ChatGame
from app.engine import Engine, EngineError
from app.game_random import GameRandom
from app.campaign_lifecycle import CampaignLifecycle
from app.recovery_probe import check_recovery


def test_portable_recovery_and_overhead_against_hosted_store_contract(hosted):
    _, _, engine, game = hosted
    state = game.create('owner-recovery-fixture', 'Recovery fixture', 'create-recovery-probe', True)
    result = check_recovery(engine, 'owner-recovery-fixture', state, 'test-recovery-probe')
    assert len(result['checks']) == 11
    assert {'compact_world_update_preserves_details', 'full_read_recovers_omitted_history'} <= set(result['checks'])
    timings = result['timings']
    assert timings['combined_state_and_approval_read']['storage_api_calls'] < timings['separate_state_and_approval_reads']['storage_api_calls']



@pytest.mark.parametrize('remote', [False, True])
def test_audit_does_not_hide_events_beyond_saved_version(remote, engine, state, hosted):
    if remote:
        _, _, engine, game = hosted
        state = game.create('owner-a', 'Audit fixture', 'create-audit-fixture', True)
    with engine.store.transaction() as db:
        first = records.get(db, 'events_v1', {'campaign_id': state['id'], 'number': 1})
        records.insert(db, 'events_v1', {**first, 'number': 2})
    assert not engine.audit('owner-a', state['id'])['integrity_valid']


class MemoryAPI:
    def __init__(self):
        self.rows, self.transactions, self.revisions = {}, {}, {}
        self.next_id = 0
        self.reject_commit = False

    @staticmethod
    def response(row):
        if row is None:
            return None
        return {**{key: value for key, value in row.items() if key.startswith('$')},
                'data': {key: value for key, value in row.items() if not key.startswith('$')}}

    def call(self, method, path, **kwargs):
        body, params = kwargs.get('json', {}), kwargs.get('params', {})
        if path == '/tablesdb/dndgpt/tables/records':
            names = {'kind', 'record_id', 'owner', 'campaign_id', 'action_id', 'guard',
                     'number', 'version', 'created_at', 'completed', 'payload'}
            return {'$permissions': [], 'rowSecurity': True,
                    'columns': [{'key': key, 'status': 'available'} for key in names]}
        if path == '/tablesdb/transactions':
            self.next_id += 1
            key = str(self.next_id)
            self.transactions[key] = {'staged': {}, 'deleted': set(), 'base': {}}
            return {'$id': key}
        if path.startswith('/tablesdb/transactions/'):
            key = path.rsplit('/', 1)[1]
            tx = self.transactions[key]
            if body.get('commit'):
                if self.reject_commit or any(self.revisions.get(k) != v for k, v in tx['base'].items()):
                    raise EngineError(409, 'storage_conflict', 'Concurrent update')
                for row_id, row in tx['staged'].items():
                    self.rows[row_id] = copy.deepcopy(row)
                    self.revisions[row_id] = self.revisions.get(row_id, 0) + 1
                for row_id in tx['deleted']:
                    self.rows.pop(row_id, None)
                    self.revisions[row_id] = self.revisions.get(row_id, 0) + 1

            self.transactions.pop(key)
            return {'$id': key}
        transaction_id = body.get('transactionId', params.get('transactionId'))
        tx = self.transactions[transaction_id]
        visible = {**self.rows, **tx['staged']}
        for row_id in tx['deleted']:
            visible.pop(row_id, None)
        if path.endswith('/rows') and method == 'GET':
            rows = list(visible.values())
            for raw in params['queries[]']:
                query = json.loads(raw)
                kind, key, values = query['method'], query.get('attribute'), query.get('values')
                if kind == 'equal':
                    rows = [row for row in rows if row.get(key) in values]
                elif kind == 'greaterThan':
                    rows = [row for row in rows if row[key] > values[0]]
                elif kind == 'lessThanEqual':
                    rows = [row for row in rows if row[key] <= values[0]]
                elif kind.startswith('order'):
                    rows.sort(key=lambda row: row[key], reverse=kind == 'orderDesc')
                elif kind == 'cursorAfter':
                    position = next(i for i, row in enumerate(rows) if row['$id'] == values[0])
                    rows = rows[position + 1:]
            limit = next(json.loads(raw)['values'][0] for raw in params['queries[]']
                         if json.loads(raw)['method'] == 'limit')
            return {'rows': [self.response(copy.deepcopy(row)) for row in rows[:limit]]}
        key = body['rowId'] if method == 'POST' else path.rsplit('/', 1)[1]
        if method == 'GET':
            return self.response(copy.deepcopy(visible.get(key)))
        if method == 'DELETE':
            if key not in visible:
                return None
            tx['base'].setdefault(key, self.revisions.get(key))
            tx['staged'].pop(key, None)
            tx['deleted'].add(key)
            return {'$id': key}

        if method == 'POST' and key in visible:
            raise EngineError(409, 'storage_conflict', 'Duplicate record')
        if method == 'PATCH' and key not in visible:
            return None
        tx['deleted'].discard(key)

        tx['base'].setdefault(key, self.revisions.get(key))
        row = {**visible.get(key, {'$id': key, '$createdAt': self.next_id}), **body['data']}
        tx['staged'][key] = copy.deepcopy(row)
        return self.response(copy.deepcopy(row))


@pytest.fixture
def hosted():
    api = MemoryAPI()
    store = AppwriteStore(api)
    store.initialize()
    engine = Engine(store)
    return api, store, engine, ChatGame(engine)


def test_roundtrip_restart_owner_and_exact_retry(hosted):
    api, store, engine, game = hosted
    state = game.create('owner-a', 'Hosted fixture', 'create-hosted-01', True)
    update = game.update('owner-a', state['id'], 'update-hosted-01', 1, 'Fixture prepared',
                         {'character': {'class_name': 'Fixture'}, 'world': {'place': 'Test room'}})
    reopened = ChatGame(Engine(AppwriteStore(api)))
    assert reopened.update('owner-a', state['id'], 'update-hosted-01', 1, 'Fixture prepared',
                           {'character': {'class_name': 'Fixture'}, 'world': {'place': 'Test room'}}) == update
    assert reopened.version('owner-a', state['id'], 1)['campaign']['version'] == 1
    assert engine.audit('owner-a', state['id'])['event_count'] == 2
    assert engine.audit('owner-a', state['id'])['integrity_valid']
    before = copy.deepcopy(api.rows)
    assert engine.list_campaigns('owner-b') == []
    with pytest.raises(EngineError, match='Campaign not found'):
        engine.get_campaign('owner-b', state['id'])
    assert before == api.rows


def test_legacy_lifecycle_receipts_remain_idempotent_without_a_creation_gate(hosted):
    api, store, engine, game = hosted
    state = game.create('owner-a', 'Hosted fixture', 'create-hosted-02', True)
    state = game.update('owner-a', state['id'], 'update-hosted-02', 1, 'Prepared',
                        {'character': {'class_name': 'Fixture'}, 'opening_preview': 'An empty test room'})['campaign']
    proposal = engine.propose_action('owner-a', state['id'], 'confirm-hosted-02', 2, 'confirm_chat_character', {})
    assert engine.pending_approval('owner-a', state['id'])['approval'] is None
    approved = engine.execute_confirmed_action('owner-a', proposal['proposal']['id'], proposal['_meta']['approval_token'])
    assert approved['campaign']['phase'] == 'ready'
    assert approved['campaign']['paused']
    assert engine.execute_confirmed_action('owner-a', proposal['proposal']['id'], proposal['_meta']['approval_token']) == approved
    proposal = engine.propose_action('owner-a', state['id'], 'adventure-hosted-02', 3, 'start_chat_adventure', {})
    approved = engine.execute_confirmed_action('owner-a', proposal['proposal']['id'], proposal['_meta']['approval_token'])
    assert approved['campaign']['phase'] == 'adventure'
    assert engine.audit('owner-a', state['id'])['integrity_valid']


def test_hosted_expired_proposal_remains_reviewable_after_restart(hosted):
    import time
    api, store, engine, game = hosted
    state = game.create('owner-a', 'Hosted expiry fixture', 'hosted-expiry-create', True)
    state = game.update('owner-a', state['id'], 'hosted-expiry-prepare', 1, 'Prepared',
                        {'character': {'class_name': 'Fixture'}})['campaign']
    proposal = engine.propose_action('owner-a', state['id'], 'hosted-expiry-review', 2, 'pause', {})
    with store.transaction() as db:
        records.update(db, 'proposals_v1', {'id': proposal['proposal']['id']}, {'created_at': time.time() - 901})
    reopened = Engine(AppwriteStore(api))
    prior = copy.deepcopy(api.rows)
    approval = reopened.pending_approval('owner-a', state['id'])['approval']
    assert approval['expired'] and 'approval_token' not in approval
    assert approval['proposal'] == proposal['proposal'] and api.rows == prior
    assert reopened.get_campaign('owner-a', state['id']) == state
    with pytest.raises(EngineError) as error:
        reopened.execute_confirmed_action('owner-a', proposal['proposal']['id'], proposal['_meta']['approval_token'])
    assert error.value.code == 'proposal_expired'


def test_direct_creation_and_outfit_roundtrip_on_hosted_store(hosted):
    from app.game_random import GameRandom
    api, store, engine, game = hosted
    state = game.create('owner-a', 'Disposable outfitting fixture', 'direct-hosted-create', True)
    state = game.update('owner-a', state['id'], 'direct-hosted-class', 1, 'Actual class choice',
                        {'character': {'class_name': 'Fixture Warden'}})['campaign']
    receipt = GameRandom(store, engine=engine).roll('owner-a', 'starting-outfit-' + state['id'],
        [{'label': 'Outfit', 'kind': 'outfitting', 'class_rarity': 'COMMON', 'slot_preferences':
          [{'slot': 'Artifact', 'weight': 2, 'basis': 'The chosen Warden class channels power through an implement'}]}], state['id'])
    plan = receipt['results'][0]['result']
    items = [{'id': f'gear-{i}', 'name': row['role'], 'rarity': row['rarity'], 'effects': ['Fixture effect']}
             for i, row in enumerate(plan['items'])]
    changes = {'character': {'background': 'Fixture keeper', 'story_summary': 'The keeper watches the crossing.'},
               'opening_preview': 'A messenger arrives.', 'upsert': {'inventory': items},
               'equipment': dict(zip((r['slot'] for r in plan['items']), [r['id'] for r in items])),
               'creation': {'outfitting': {'item_ids': [r['id'] for r in items]}}}
    result = game.update('owner-a', state['id'], 'direct-hosted-finish', state['version'],
                         'Complete choices directly', changes, begin_adventure=True)
    assert result['campaign']['phase'] == 'adventure' and not result['campaign']['paused']
    reopened = ChatGame(Engine(AppwriteStore(api)))
    assert reopened.update('owner-a', state['id'], 'direct-hosted-finish', state['version'],
                            'Complete choices directly', changes, begin_adventure=True) == result
    assert engine.audit('owner-a', state['id'])['event_count'] == 3


def test_failed_commit_does_not_leave_partial_state(hosted):
    api, store, engine, game = hosted
    state = game.create('owner-a', 'Hosted fixture', 'create-hosted-03', True)
    prior = copy.deepcopy(api.rows)
    api.reject_commit = True
    with pytest.raises(EngineError, match='Concurrent update'):
        game.update('owner-a', state['id'], 'update-hosted-03', 1, 'Not committed', {'notes': 'Uncommitted'})
    assert api.rows == prior
    assert not api.transactions
    api.reject_commit = False
    assert game.update('owner-a', state['id'], 'update-hosted-03', 1, 'Not committed', {'notes': 'Uncommitted'})['campaign']['version'] == 2


def test_staged_read_guard_rejects_competing_writer(hosted):
    api, store, engine, game = hosted
    state = game.create('owner-a', 'Hosted fixture', 'create-hosted-04', True)
    with pytest.raises(EngineError, match='Concurrent update'):
        with store.transaction() as db:
            row = records.get(db, 'campaigns_v1', {'id': state['id'], 'owner': 'owner-a'})
            game.update('owner-a', state['id'], 'winner-hosted-04', 1, 'Winner', {'notes': 'winner'})
            records.update(db, 'campaigns_v1', {'id': state['id']}, {'data': row['data']})
    assert engine.get_campaign('owner-a', state['id'])['notes'] == 'winner'
    assert engine.audit('owner-a', state['id'])['integrity_valid']


def test_reads_and_preferences_have_no_game_effect(hosted):
    api, store, engine, game = hosted
    state = game.create('owner-a', 'Hosted fixture', 'create-hosted-05', True)
    prior = copy.deepcopy(api.rows)
    assert engine.dashboard('owner-a', state['id'])['campaign']['version'] == 1
    assert api.rows == prior
    preferences = {'panels': [], 'details': [], 'hud_hidden': False, 'world_tab': 'log'}
    engine.set_view_preferences('owner-a', preferences)
    assert engine.get_view_preferences('owner-a') == preferences
    assert Engine(AppwriteStore(api)).get_view_preferences('owner-a') == preferences
    assert engine.audit('owner-a', state['id'])['event_count'] == 1


def test_roll_receipts_survive_reopen_without_campaign_change(hosted):
    api, store, engine, game = hosted
    random = GameRandom(store)
    rolls = [{'kind': 'dice', 'label': 'Disposable fixture', 'sides': 6, 'count': 1}]
    result = random.roll('owner-a', 'fixture-roll-001', rolls)
    assert GameRandom(AppwriteStore(api)).roll('owner-a', 'fixture-roll-001', rolls) == result
    assert engine.list_campaigns('owner-a') == []
    with pytest.raises(EngineError, match='Roll receipt not found'):
        random.get('owner-b', 'fixture-roll-001')


def test_hosted_campaign_delete_compacts_linked_records(hosted):
    api, store, engine, game = hosted
    state = engine.create_sandbox("owner-a", "Hosted deletion fixture", "hosted-delete-create")
    random = GameRandom(store, engine.dice, engine)
    rolls = [{"kind": "dice", "label": "Disposable fixture", "sides": 6, "count": 1}]
    random.roll("owner-a", "hosted-delete-roll", rolls, campaign_id=state["id"])

    lifecycle = CampaignLifecycle(engine)
    preview = lifecycle.preview_delete("owner-a", state["id"], state["version"])
    result = lifecycle.delete("owner-a", state["id"], state["version"],
                              preview["confirmation_token"], True)
    assert result["deleted"] is True
    assert result["compacted_receipts"] == 1
    assert engine.list_campaigns("owner-a") == []

    with store.transaction() as db:
        assert records.find(db, "events_v1", {"campaign_id": state["id"]}) == []
        receipt = records.get(db, "game_rolls_v1", {
            "owner": "owner-a", "action_id": "hosted-delete-roll"
        })
        assert receipt["campaign_id"] == ""
        assert json.loads(receipt["result"]) == {
            "_campaign_deleted": True, "campaign_id": state["id"]
        }

    with pytest.raises(EngineError) as deleted:
        engine.create_sandbox("owner-a", "Hosted deletion fixture", "hosted-delete-create")
    assert deleted.value.code == "campaign_deleted"



def test_paginated_events_are_not_truncated(hosted):
    api, store, engine, game = hosted
    with store.transaction() as db:
        for i in range(205):
            records.insert(db, 'events_v1', {'campaign_id': 'fixture-campaign', 'number': i + 1,
                                           'event': '{}', 'previous_hash': '', 'hash': ''})
    with store.transaction() as db:
        rows = records.find(db, 'events_v1', {'campaign_id': 'fixture-campaign'}, order='number')
    assert [row['number'] for row in rows] == list(range(1, 206))


def test_provider_errors_do_not_expose_credentials():
    def handler(request):
        return httpx.Response(403, json={'message': 'secret-provider-key'})
    client = httpx.Client(transport=httpx.MockTransport(handler))
    api = AppwriteAPI('https://fixture.appwrite.io/v1', 'fixture', 'secret-provider-key', client=client)
    with pytest.raises(EngineError) as error:
        api.call('GET', '/tablesdb/fixture')
    assert error.value.status == 503
    assert 'secret-provider-key' not in str(error.value)


class Response:
    def binary(self, body, status=200, headers=None):
        return SimpleNamespace(body=body, status=status, headers=headers or {})

    def json(self, body, status=200, headers=None):
        return self.binary(json.dumps(body).encode(), status, headers)


def context(path='/probe', host='fixture.example', body=b''):
    return SimpleNamespace(req=SimpleNamespace(path=path, host=host, method='POST',
                           body_binary=body, query_string='', headers={'host': host}), res=Response())


def test_function_bridge_preserves_http_status_headers_and_bytes():
    from fastapi.responses import Response as HTTPResponse
    application = FastAPI()
    @application.post('/probe')
    def probe():
        return HTTPResponse(b'{"fixture":true}', status_code=401,
                            headers={'www-authenticate': 'Bearer resource_metadata="https://fixture.example/metadata"'},
                            media_type='application/json')
    result = asyncio.run(dispatch(context(), application, 'https://fixture.example/mcp'))
    assert result.status == 401
    assert result.body == b'{"fixture":true}'
    assert 'www-authenticate' in result.headers
    assert 'content-length' not in result.headers


def test_function_bridge_rejects_foreign_host():
    result = asyncio.run(dispatch(context(host='attacker.example'), FastAPI(), 'https://fixture.example/mcp'))
    assert result.status == 421


def test_function_bridge_rejects_oversized_body():
    result = asyncio.run(dispatch(context(body=b'x' * 2500001), FastAPI(), 'https://fixture.example/mcp'))
    assert result.status == 413


def test_missing_hosted_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv('APPWRITE_FUNCTION_API_ENDPOINT', raising=False)
    result = asyncio.run(main(context('/mcp')))
    assert result.status == 503


def test_function_entrypoint_uses_the_existing_runtime_loop(monkeypatch, hosted):
    from app import appwrite_entry
    for key, value in {
        'APPWRITE_FUNCTION_API_ENDPOINT': 'https://fixture.example/v1',
        'APPWRITE_FUNCTION_PROJECT_ID': 'fixture',
        'DNDGPT_ENV': 'production',
        'DNDGPT_RESOURCE_URL': 'https://fixture.example/mcp',
        'DNDGPT_OAUTH_ISSUER': 'https://issuer.example/',
        'DNDGPT_JWKS_URL': 'https://issuer.example/.well-known/jwks.json',
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(appwrite_entry, 'AppwriteAPI', lambda *args, **kwargs: hosted[0])
    async def invoke():
        health = context('/api/health')
        health.req.method = 'GET'
        assert (await main(health)).status == 200
        denied = await main(context('/mcp'))
        assert denied.status == 401
        assert 'resource_metadata=' in denied.headers['www-authenticate']
    asyncio.run(invoke())


def test_hosted_factory_does_not_create_local_database(hosted, tmp_path):
    from app.auth import AuthConfig
    from app.server import create_app
    from fastapi.testclient import TestClient
    api, store, engine, game = hosted
    with TestClient(create_app(auth_config=AuthConfig(), store=store)) as client:
        assert client.get('/api/health').status_code == 200
        assert client.post('/mcp', json={}).status_code == 503
    assert list(tmp_path.iterdir()) == []


def test_signed_http_and_mcp_use_hosted_owner_records(hosted, config, verifier, tokens):
    from app.server import create_app
    from fastapi.testclient import TestClient
    api, store, engine, game = hosted
    application = create_app(auth_config=config, token_verifier=verifier, store=store)
    headers = {'Authorization': 'Bearer ' + tokens()}
    with TestClient(application, base_url='https://dndgpt.example.test', headers=headers) as client:
        assert client.get('/api/campaigns', headers={'Authorization': ''}).status_code == 401
        created = client.post('/api/chat-games', json={'name': 'Hosted HTTP fixture',
                              'action_id': 'hosted-http-create', 'disposable': True})
        assert created.status_code == 200
        campaign_id = created.json()['campaign']['id']
        other = {'Authorization': 'Bearer ' + tokens(subject='user-b')}
        assert client.get('/api/campaigns/' + campaign_id, headers=other).status_code == 404
        assert client.post('/api/chat-games', json={'name': 'Denied', 'action_id': 'denied-read-only'},
                           headers={'Authorization': 'Bearer ' + tokens(scopes='campaign:read')}).status_code == 403
        response = client.post('/mcp', headers={'Accept': 'application/json, text/event-stream'},
                                json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                      'params': {'name': 'render_dashboard', 'arguments': {'campaign_id': campaign_id}}})
        assert response.status_code == 200
        result = response.json()['result']
        assert not result.get('isError')
        assert result['structuredContent']['campaign']['id'] == campaign_id
        response = client.post('/mcp', headers={'Accept': 'application/json, text/event-stream'},
                                json={'jsonrpc': '2.0', 'id': 2, 'method': 'resources/read',
                                      'params': {'uri': application.state.resource_uri}})
        assert response.status_code == 200
        assert response.json()['result']['contents'][0]['text'].count('data-panel="') == 9
