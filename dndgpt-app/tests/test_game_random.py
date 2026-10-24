import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.engine import Engine, EngineError
from app.game_random import GameRandom
from app.rules import Dice
from app.storage import Store
from tests.test_server import rpc, tool


def toolbox(tmp_path, draws):
    store = Store(tmp_path / 'random.sqlite3')
    store.initialize()
    consumed = []
    iterator = iter(draws)
    def draw(sides):
        consumed.append(sides)
        return next(iterator)
    return GameRandom(store, Dice(draw)), consumed


def test_batch_reuses_rules_and_does_not_change_campaign(tmp_path):
    box, consumed = toolbox(tmp_path, [0, 5, 2, 18, 9999, 0])
    engine = Engine(box.store)
    state = engine.create_sandbox('owner-a', 'Untouched paused fixture', 'create-untouched')
    receipt = box.roll('owner-a', 'batch-all-kinds', [
        {'label': 'damage', 'kind': 'dice', 'sides': 6, 'count': 2, 'modifier': 2},
        {'label': 'check', 'kind': 'check', 'dc': 15, 'advantage': True},
        {'label': 'rarity', 'kind': 'rarity', 'luck': 9}])
    assert receipt['results'][0]['result']['total'] == 9
    assert receipt['results'][1]['result']['natural'] == 19
    assert receipt['results'][2]['result'] == {'final_rarity': 'UNIQUE', 'enhanced': True}
    assert len(consumed) == 6
    assert engine.get_campaign('owner-a', state['id']) == state
    assert engine.audit('owner-a', state['id'])['event_count'] == 1


def test_retry_after_reopen_recovers_exact_receipt_and_conflicts_do_not_draw(tmp_path):
    box, consumed = toolbox(tmp_path, [19])
    rolls = [{'label': 'attack', 'kind': 'dice', 'sides': 20}]
    first = box.roll('owner-a', 'same-roll-action', rolls)
    reopened = GameRandom(Store(box.store.path), Dice(lambda _: pytest.fail('Rerolled saved action')))
    assert reopened.roll('owner-a', 'same-roll-action', rolls) == first
    assert reopened.get('owner-a', 'same-roll-action') == first
    with pytest.raises(EngineError) as error:
        reopened.roll('owner-a', 'same-roll-action', [{'label': 'attack', 'kind': 'dice', 'sides': 6}])
    assert error.value.code == 'idempotency_conflict' and consumed == [20]


def test_pre_update_rarity_receipt_keeps_its_original_tier(tmp_path):
    from app import records
    from app.storage import canonical
    box, consumed = toolbox(tmp_path, [])
    rolls = [{'label': 'Original issued offer', 'kind': 'rarity', 'luck': 5}]
    old = {'action_id': 'pre-power-fantasy-roll', 'rng': 'recorded earlier',
           'results': [{'label': rolls[0]['label'], 'kind': 'rarity', 'result': {
               'natural': 5000, 'base_rarity': 'COMMON', 'final_rarity': 'COMMON',
               'luck': 5, 'luck_roll': None, 'enhanced': False}}]}
    with box.store.transaction() as db:
        records.insert(db, 'game_rolls_v1', {'owner': 'owner-a', 'action_id': old['action_id'],
            'campaign_id': '', 'request': canonical(rolls), 'result': canonical(old)})
    # Under the new table this natural result is UNCOMMON; its saved outcome stays COMMON.
    assert box.roll('owner-a', old['action_id'], rolls) == GameRandom.public(old)
    assert box.get('owner-a', old['action_id'], True)['results'][0]['result']['base_rarity'] == 'COMMON'
    assert not consumed


@pytest.mark.parametrize('bad', [
    [], [{'label': 'bad', 'kind': 'dice', 'sides': True}],
    [{'label': 'bad', 'kind': 'dice', 'sides': 6, 'count': 0}],
    [{'label': 'bad', 'kind': 'check', 'dc': 12, 'advantage': 1}],
    [{'label': 'bad', 'kind': 'rarity', 'luck': -1}],
    [{'label': 'bad', 'kind': 'rarity', 'luck': 0}],
    [{'label': 'bad', 'kind': 'rarity', 'luck': 21}],
    [{'label': 'bad', 'kind': 'dice', 'sides': 6, 'python': 'print(1)'}],
    [{'label': 'duplicate', 'kind': 'dice', 'sides': 6}] * 2,
    [{'label': 'bad', 'kind': 'unknown'}],
])
def test_whole_batch_validated_before_any_random_draw(tmp_path, bad):
    box, consumed = toolbox(tmp_path, [])
    rows = [{'label': 'first', 'kind': 'dice', 'sides': 20}] + bad if bad else bad
    with pytest.raises(EngineError):
        box.roll('owner-a', 'invalid-request', rows)
    assert not consumed
    with box.store.transaction() as db:
        assert db.execute('SELECT count(*) FROM game_rolls_v1').fetchone()[0] == 0


def test_owner_isolation_and_explicit_raw_rarity_recovery(tmp_path):
    box, _ = toolbox(tmp_path, [9999, 1])
    receipt = box.roll('owner-a', 'private-rarity', [{'label': 'private', 'kind': 'rarity', 'luck': 1}])
    assert 'natural' not in json.dumps(receipt)
    assert box.get('owner-a', 'private-rarity', True)['results'][0]['result']['natural'] == 10000
    with pytest.raises(EngineError) as error:
        box.get('owner-b', 'private-rarity', True)
    assert error.value.status == 404
    assert box.roll('owner-b', 'private-rarity', [{'label': 'other', 'kind': 'dice', 'sides': 6}])['results'][0]['result']['total'] == 2


def test_concurrent_retry_draws_once(tmp_path):
    box, consumed = toolbox(tmp_path, [3])
    rolls = [{'label': 'once', 'kind': 'dice', 'sides': 6}]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: box.roll('owner-a', 'concurrent-roll', rolls), range(2)))
    assert results[0] == results[1] and consumed == [6]


def test_signed_mcp_batch_retry_scope_and_receipt_ownership(web, tokens):
    definitions = {t['name']: t for t in rpc(web, 'tools/list')['tools']}
    assert definitions['roll_game_random']['annotations']['idempotentHint']
    args = {'action_id': 'signed-game-roll', 'rolls': [{'label': 'test only', 'kind': 'dice', 'sides': 20}]}
    result = tool(web, 'roll_game_random', args)
    assert not result.get('isError'), result
    assert tool(web, 'roll_game_random', args)['structuredContent'] == result['structuredContent']
    denied = rpc(web, 'tools/call', {'name': 'roll_game_random', 'arguments': dict(args, action_id='read-only-denied')},
                 headers={'Authorization': 'Bearer ' + tokens(scopes='campaign:read')})
    assert denied['isError'] and 'insufficient_scope' in str(denied['_meta'])
    denied = rpc(web, 'tools/call', {'name': 'get_game_roll', 'arguments': {'action_id': args['action_id']}},
                 headers={'Authorization': 'Bearer ' + tokens(subject='user-b')})
    assert denied['isError'] and denied['structuredContent']['status'] == 404
    assert tool(web, 'get_game_roll', {'action_id': args['action_id']})['structuredContent'] == result['structuredContent']
