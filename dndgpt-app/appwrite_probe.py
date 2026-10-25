"""Private Appwrite execution probe. Never use as the public entrypoint."""
import hashlib
import io
import json
import os
import time
import traceback
import uuid

import httpx
from PIL import Image

if __package__:
    from .app.appwrite_store import AppwriteAPI, AppwriteStore
    from .app.chat_game import ChatGame
    from .app.engine import Engine, EngineError
    from .app.game_random import GameRandom
    from .app.recovery_probe import check_recovery
    from .app.gallery import Gallery, GalleryFile
    from .app.version import APP_VERSION
else:
    from app.appwrite_store import AppwriteAPI, AppwriteStore
    from app.chat_game import ChatGame
    from app.engine import Engine, EngineError
    from app.game_random import GameRandom
    from app.recovery_probe import check_recovery
    from app.gallery import Gallery, GalleryFile
    from app.version import APP_VERSION


def check_public_connection(client, resource_url):
    origin = resource_url.removesuffix('/mcp')
    health = client.get(origin + '/api/health', params={'probe': uuid.uuid4().hex})
    assert health.status_code == 200 and health.json().get('version') == APP_VERSION
    metadata = client.get(origin + '/.well-known/oauth-protected-resource/mcp')
    assert metadata.status_code == 200 and metadata.json().get('resource') == resource_url
    denied = client.post(resource_url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
    assert denied.status_code == 401 and 'resource_metadata=' in denied.headers.get('www-authenticate', '')
    return ['public_http_health', 'public_oauth_metadata', 'public_anonymous_denial']


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
            random = GameRandom(store, engine=engine)
            outfit = random.roll(owner, 'starting-outfit-' + state['id'],
                                 [{'kind': 'outfitting', 'label': 'Disposable starting equipment',
                                   'class_rarity': 'COMMON', 'slot_preferences': [
                                       {'slot': 'Artifact', 'weight': 3,
                                        'basis': 'The disposable inspection class uses a calibration implement'}]}],
                                 campaign_id=state['id'])
            plan = outfit['results'][0]['result']
            items = [{'id': 'fixture-outfit-' + str(i), 'name': 'Disposable ' + row['role'],
                      'rarity': row['rarity'], 'effects': 'Recorded equipment fixture effect.'}
                     for i, row in enumerate(plan['items'])]
            checks.append('starting_outfit_draw')
            begun = game.update(owner, state['id'], 'begin-' + run, 2, 'Finish disposable creation',
                                {'character': {'background': 'Disposable test background',
                                               'story_summary': 'A test character in the disposable probe room.'},
                                 'upsert': {'inventory': items},
                                 'equipment': {row['slot']: item['id'] for row, item in zip(plan['items'], items)},
                                 'creation': {'outfitting': {**plan, 'item_ids': [item['id'] for item in items]}},
                                 'begin_adventure': True})
            assert begun['campaign']['phase'] == 'adventure' and not begun['campaign']['paused']
            assert engine.pending_approval(owner, state['id'])['approval'] is None
            checks += ['direct_creation', 'cached_schema_creation_start', 'no_creation_approval']
            proposal = engine.propose_action(owner, state['id'], 'correct-' + run, 3, 'correct_chat_state',
                                            {'changes': {'character': {'hp': 59}}, 'reason': 'Disposable correction test'})
            assert engine.pending_approval(owner, state['id'])['approval']
            result = engine.execute_confirmed_action(owner, proposal['proposal']['id'], proposal['_meta']['approval_token'])
            assert result['campaign']['character']['hp'] == 59
            assert engine.execute_confirmed_action(owner, proposal['proposal']['id'], proposal['_meta']['approval_token']) == result
            checks += ['correction_approval', 'correction_retry']
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
            image = io.BytesIO()
            Image.new('RGB', (16, 16), '#30543d').save(image, 'PNG')
            gallery = Gallery(engine, downloader=lambda _: image.getvalue())
            saved_image = gallery.save(owner, state['id'], 'gallery-' + run, 'Disposable Gallery check',
                source_kind='generated', file=GalleryFile(download_url='https://fixture.example.test/image.png', file_id='fixture-' + run))
            image_id = saved_image['gallery_entry']['id']
            reopened_gallery = Gallery(Engine(AppwriteStore(store.api)))
            assert reopened_gallery.list(owner, state['id'])['gallery_items'][0]['id'] == image_id
            assert reopened_gallery.image(owner, state['id'], image_id, 'full')['_meta']['gallery_image'].startswith('data:image/webp;base64,')
            assert engine.get_campaign(owner, state['id']) == result['campaign']
            checks += ['gallery_file_save', 'gallery_reopen', 'gallery_no_gameplay_change']
            recovery = check_recovery(engine, owner, result['campaign'], run)
            public_url = os.getenv('DNDGPT_PUBLIC_RESOURCE_URL')
            if public_url:
                checks += check_public_connection(client, public_url)
            report = {'status': 'passed', 'checks': checks, 'recovery': recovery,
                      'elapsed_seconds': round(time.monotonic() - started, 2),
                      'real_campaign_accessed': False, 'model_api_calls': False}
            context.log(json.dumps(report))
            return context.res.json(report)
        except (EngineError, AssertionError, ValueError) as error:
            context.error('Completed checks: ' + repr(checks if 'checks' in locals() else []) + '\n' + traceback.format_exc(limit=4))
            return context.res.json({'status': 'failed', 'code': getattr(error, 'code', type(error).__name__),
                                     'completed_checks': checks if 'checks' in locals() else []}, 500)
