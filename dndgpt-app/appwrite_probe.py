"""Private Appwrite execution probe. Never use as the public entrypoint."""
import hashlib
import os
import time
import uuid

import httpx

if __package__:
    from .app.appwrite_store import AppwriteAPI, AppwriteStore
    from .app.chat_game import ChatGame
    from .app.engine import Engine, EngineError
    from .app.game_random import GameRandom
else:
    from app.appwrite_store import AppwriteAPI, AppwriteStore
    from app.chat_game import ChatGame
    from app.engine import Engine, EngineError
    from app.game_random import GameRandom


def main(context):
    started = time.monotonic()
    run = uuid.uuid4().hex
    owner = hashlib.sha256(('disposable-cloud-probe:' + run).encode()).hexdigest()
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        store = AppwriteStore(AppwriteAPI(os.environ['APPWRITE_FUNCTION_API_ENDPOINT'],
                              os.environ['APPWRITE_FUNCTION_PROJECT_ID'],
                              context.req.headers['x-appwrite-key'], client=client))
        try:
            store.initialize()
            engine, checks = Engine(store), []
            game = ChatGame(engine)
            state = game.create(owner, 'Disposable Appwrite hosting probe', 'create-' + run, True)
            checks.append('create')
            changes = {'character': {'class_name': 'Hosting fixture'}, 'world': {'fixture': True},
                       'opening_preview': 'Disposable test room; no campaign imported'}
            saved = game.update(owner, state['id'], 'update-' + run, 1, 'Hosting probe only', changes)
            assert game.update(owner, state['id'], 'update-' + run, 1, 'Hosting probe only', changes) == saved
            checks += ['save', 'exact_retry']
            assert game.version(owner, state['id'], 1)['campaign']['version'] == 1
            checks.append('historical_version')
            proposal = engine.propose_action(owner, state['id'], 'confirm-' + run, 2, 'confirm_chat_character', {})
            assert engine.pending_approval(owner, state['id'])['approval']
            confirmed = engine.execute_confirmed_action(owner, proposal['proposal']['id'], proposal['_meta']['approval_token'])
            assert confirmed['campaign']['phase'] == 'ready' and confirmed['campaign']['paused']
            assert engine.execute_confirmed_action(owner, proposal['proposal']['id'], proposal['_meta']['approval_token']) == confirmed
            checks += ['pending_approval', 'separate_confirmation', 'approval_retry']
            proposal = engine.propose_action(owner, state['id'], 'start-' + run, 3, 'start_chat_adventure', {})
            result = engine.execute_confirmed_action(owner, proposal['proposal']['id'], proposal['_meta']['approval_token'])
            assert result['campaign']['phase'] == 'adventure'
            checks.append('separate_adventure_gate')
            assert Engine(AppwriteStore(store.api)).get_campaign(owner, state['id']) == result['campaign']
            checks.append('fresh_instance_reopen')
            other = hashlib.sha256(('different-probe-owner:' + run).encode()).hexdigest()
            assert engine.list_campaigns(other) == []
            try:
                engine.get_campaign(other, state['id'])
                raise AssertionError('Cross-owner read was allowed')
            except EngineError as error:
                assert error.status == 404
            checks.append('owner_isolation')
            view = engine.dashboard(owner, state['id'])
            assert view['campaign']['version'] == 4
            checks.append('dashboard_state')
            preferences = {'panels': [], 'details': [], 'hud_hidden': False, 'world_tab': 'log'}
            engine.set_view_preferences(owner, preferences)
            assert engine.get_view_preferences(owner) == preferences
            checks.append('view_preferences')
            rolls = [{'kind': 'dice', 'label': 'Disposable hosting fixture', 'sides': 6, 'count': 1}]
            random = GameRandom(store)
            roll = random.roll(owner, 'roll-' + run, rolls)
            assert GameRandom(AppwriteStore(store.api)).roll(owner, 'roll-' + run, rolls) == roll
            checks.append('durable_roll_retry')
            audit = engine.audit(owner, state['id'])
            assert audit['integrity_valid'] and audit['event_count'] == 4
            checks.append('event_integrity')
            return context.res.json({'status': 'passed', 'checks': checks,
                                     'elapsed_seconds': round(time.monotonic() - started, 2),
                                     'real_campaign_accessed': False, 'model_api_calls': False})
        except (EngineError, AssertionError, ValueError) as error:
            context.error(type(error).__name__ + ': ' + str(error))
            return context.res.json({'status': 'failed', 'code': getattr(error, 'code', type(error).__name__),
                                     'completed_checks': checks if 'checks' in locals() else []}, 500)
