"""Reusable, account-scoped Python rolls for a chat-led GM; no campaign mutation."""
import json
from datetime import datetime, timezone

from .engine import fail, identifier
from .rules import Dice, integer
from .storage import canonical
from . import records
from .outfitting import BUDGETS, slot_pool, starting_outfit
from .world_events import CHANCES, valid_id, validate_pool, draw_event


class GameRandom:
    def __init__(self, store, dice=None, engine=None):
        self.store, self.dice, self.engine = store, dice or Dice(), engine

    @staticmethod
    def validate(rolls):
        if type(rolls) is not list or not 1 <= len(rolls) <= 20:
            raise ValueError('rolls must contain1..20 requests')
        labels = set()
        outfitting_count = 0
        event_count = 0
        for row in rolls:
            if type(row) is not dict:
                raise ValueError('Each roll must be an object')
            label, kind = row.get('label'), row.get('kind')
            if type(label) is not str or not 1 <= len(label.strip()) <= 120 or label in labels:
                raise ValueError('Roll labels must be unique nonblank text of at most120 characters')
            labels.add(label)
            allowed = {'dice': {'sides', 'count', 'modifier'},
                       'check': {'dc', 'modifier', 'advantage', 'disadvantage'},
                       'rarity': {'luck'}, 'outfitting': {'class_rarity', 'slot_preferences'},
                       'world_event': {'context', 'transition_id', 'pool', 'pool_action_id'}}
            if type(kind) is not str or kind not in allowed or set(row) - allowed[kind] - {'label', 'kind'}:
                raise ValueError('Unknown roll kind or unexpected fields')
            if kind == 'dice':
                integer(row.get('sides'), 2, 10000, 'sides')
                integer(row.get('count', 1), 1, 20, 'count')
                integer(row.get('modifier', 0), -10000, 10000, 'modifier')
            elif kind == 'check':
                integer(row.get('dc'), 1, 40, 'dc')
                integer(row.get('modifier', 0), -20, 40, 'modifier')
                for key in ('advantage', 'disadvantage'):
                    if type(row.get(key, False)) is not bool:
                        raise ValueError(key + ' must be boolean')
            elif kind == 'rarity':
                integer(row.get('luck'), 1, 20, 'luck score')
            elif kind == 'world_event':
                event_count += 1
                if (event_count > 1 or row.get('context') not in CHANCES or
                        not valid_id(row.get('transition_id')) or
                        ('pool' in row) == ('pool_action_id' in row)):
                    raise ValueError('One world_event needs context, transition_id and either pool or pool_action_id')
                if 'pool' in row:
                    validate_pool(row['pool'])
                elif type(row['pool_action_id']) is not str or not row['pool_action_id']:
                    raise ValueError('Reuse the recorded original pool_action_id')
            elif row.get('class_rarity') not in BUDGETS:
                raise ValueError('outfitting requires a recorded class_rarity')
            else:
                if 'slot_preferences' in row:
                    slot_pool(row['slot_preferences'])
                outfitting_count += 1
                if outfitting_count > 1:
                    raise ValueError('A campaign has one starting-equipment draw')

    @staticmethod
    def public(receipt, show_rolls=False):
        result = json.loads(canonical(receipt))
        result['raw_rarity_rolls_included'] = show_rolls
        if not show_rolls:
            for row in result['results']:
                if row['kind'] == 'rarity':
                    row['result'] = {key: row['result'][key] for key in ('final_rarity', 'enhanced')}
                elif row['kind'] == 'outfitting':
                    for item in row['result']['items']:
                        item.pop('roll', None)
                        item.pop('slot_roll', None)
        for row in result['results']:
            if row['kind'] == 'world_event':
                row['result'].pop('_event_pool', None)  # Unchosen future events stay server-side.
        return result

    def roll(self, owner, action_id, rolls, campaign_id=None):
        identifier(action_id, 'action_id')
        if campaign_id is not None:
            identifier(campaign_id, 'campaign_id')
            if self.engine is None:
                fail(503, 'campaign_unavailable', 'Campaign-bound rolls require the campaign engine')
        try:
            self.validate(rolls)
            if len(canonical(rolls).encode()) > 250000:
                raise ValueError('Roll batch exceeds 250000 bytes; reuse a saved regional event pool')
            event = next((row for row in rolls if row['kind'] == 'world_event'), None)
            if event and (not campaign_id or action_id != 'event-' + campaign_id + '-' + event['transition_id']):
                raise ValueError('Use action_id=event-<campaign_id>-<transition_id> for a world event')
            if any(row['kind'] == 'outfitting' for row in rolls):
                if campaign_id is None or action_id != 'starting-outfit-' + campaign_id:
                    raise ValueError('Use action_id=starting-outfit-<campaign_id> for the one starting outfit')
            request = canonical(rolls) if campaign_id is None else canonical(
                {'campaign_id': campaign_id, 'rolls': rolls})
        except (ValueError, TypeError) as error:
            fail(422, 'invalid_roll_request', str(error))
        with self.store.transaction() as db:
            if campaign_id is not None:
                self.engine._get(db, owner, campaign_id)
            prior = records.get(db, 'game_rolls_v1', {'owner': owner, 'action_id': action_id})
            if prior:
                previous = json.loads(prior['result'])
                if previous.get('_campaign_deleted'):
                    fail(410, 'campaign_deleted', 'This campaign-bound roll receipt was deleted')
                if prior['request'] != request:
                    fail(409, 'idempotency_conflict', 'action_id already has different roll arguments')
                return self.public(previous)
            event_pool = None
            if event:
                state = self.engine._get(db, owner, campaign_id)
                if state.get('phase') != 'adventure' or state.get('paused') or state.get('level_up_freeze'):
                    fail(423, 'event_clock_frozen', 'Event checks need active adventure time')
                pool_id = event.get('pool_action_id', action_id)
                if 'pool' in event:
                    event_pool = event['pool']
                else:
                    saved = records.get(db, 'game_rolls_v1', {'owner': owner, 'action_id': pool_id})
                    if saved and saved.get('campaign_id') == campaign_id:
                        stored = json.loads(saved['result'])
                        event_pool = next((r['result'].get('_event_pool') for r in stored.get('results', [])
                                           if r['kind'] == 'world_event' and r['result'].get('_event_pool')), None)
                    if event_pool is None:
                        fail(422, 'event_pool_required', 'Use the original pool_action_id from this campaign')
            outfit = next((row for row in rolls if row['kind'] == 'outfitting'), None)
            if outfit:
                state = self.engine._get(db, owner, campaign_id)
                if state.get('mode') != 'chat' or state.get('phase') not in {'character_draft', 'ready'}:
                    fail(409, 'wrong_phase', 'Starting equipment is drawn during creation only')
                if state['character']['class_name'] == 'Unassigned':
                    fail(422, 'class_required', 'Save the selected class before drawing its equipment')
                if state['character']['rarity'] != outfit['class_rarity']:
                    fail(422, 'rarity_mismatch', 'Use the saved class rarity for starting equipment')
                if state.get('creation', {}).get('outfitting'):
                    fail(409, 'outfitting_exists', 'Reuse the saved starting-equipment receipt')
                if 'slot_preferences' not in outfit:
                    fail(422, 'slot_preferences_required',
                         'Precommit class/story slot_preferences with slot, weight (0..3) and basis')
            results = []
            for row in rolls:
                kind = row['kind']
                if kind == 'dice':
                    values = [self.dice.roll(row['sides']) for _ in range(row.get('count', 1))]
                    result = {'rolls': values, 'modifier': row.get('modifier', 0),
                              'total': sum(values) + row.get('modifier', 0)}
                elif kind == 'check':
                    result = self.dice.check(row['dc'], row.get('modifier', 0),
                                             row.get('advantage', False), row.get('disadvantage', False))
                elif kind == 'rarity':
                    result = self.dice.rarity(row['luck'])
                elif kind == 'outfitting':
                    result = starting_outfit(row['class_rarity'], self.dice, row['slot_preferences'])
                else:
                    used = state.get('event_tracking', {}).get('used_events', {}).get(pool_id, [])
                    result = draw_event(row['context'], row['transition_id'], event_pool, pool_id, used, self.dice)
                    if 'pool' in row:
                        result['_event_pool'] = event_pool
                results.append({'label': row['label'], 'kind': kind, 'result': result})
            receipt = {'action_id': action_id, 'results': results, 'rng': self.dice.source,
                       'created_at': datetime.now(timezone.utc).isoformat(), 'campaign_changed': False}
            records.insert(db, 'game_rolls_v1', {'owner': owner, 'action_id': action_id,
                                               'campaign_id': campaign_id or '',
                                               'request': request, 'result': canonical(receipt)})
            return self.public(receipt)

    def get(self, owner, action_id, show_rolls=False):
        identifier(action_id, 'action_id')
        if type(show_rolls) is not bool:
            fail(422, 'invalid_roll_request', 'show_rolls must be boolean')
        with self.store.transaction() as db:
            row = records.get(db, 'game_rolls_v1', {'owner': owner, 'action_id': action_id})
            if row is None:
                fail(404, 'not_found', 'Roll receipt not found')
            result = json.loads(row['result'])
            if result.get('_campaign_deleted'):
                fail(410, 'campaign_deleted', 'This campaign-bound roll receipt was deleted')
            return self.public(result, show_rolls)
