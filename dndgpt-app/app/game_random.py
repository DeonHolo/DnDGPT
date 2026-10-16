"""Reusable, account-scoped Python rolls for a chat-led GM; no campaign mutation."""
import json
from datetime import datetime, timezone

from .engine import fail, identifier
from .rules import Dice, integer
from .storage import canonical
from . import records


class GameRandom:
    def __init__(self, store, dice=None):
        self.store, self.dice = store, dice or Dice()

    @staticmethod
    def validate(rolls):
        if type(rolls) is not list or not 1 <= len(rolls) <= 20:
            raise ValueError('rolls must contain1..20 requests')
        labels = set()
        for row in rolls:
            if type(row) is not dict:
                raise ValueError('Each roll must be an object')
            label, kind = row.get('label'), row.get('kind')
            if type(label) is not str or not 1 <= len(label.strip()) <= 120 or label in labels:
                raise ValueError('Roll labels must be unique nonblank text of at most120 characters')
            labels.add(label)
            allowed = {'dice': {'sides', 'count', 'modifier'},
                       'check': {'dc', 'modifier', 'advantage', 'disadvantage'},
                       'rarity': {'luck'}}
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
            else:
                integer(row.get('luck'), 1, 20, 'luck score')

    @staticmethod
    def public(receipt, show_rolls=False):
        result = json.loads(canonical(receipt))
        result['raw_rarity_rolls_included'] = show_rolls
        if not show_rolls:
            for row in result['results']:
                if row['kind'] == 'rarity':
                    row['result'] = {key: row['result'][key] for key in ('final_rarity', 'enhanced')}
        return result

    def roll(self, owner, action_id, rolls):
        identifier(action_id, 'action_id')
        try:
            self.validate(rolls)
            request = canonical(rolls)
        except (ValueError, TypeError) as error:
            fail(422, 'invalid_roll_request', str(error))
        with self.store.transaction() as db:
            prior = records.get(db, 'game_rolls_v1', {'owner': owner, 'action_id': action_id})
            if prior:
                if prior['request'] != request:
                    fail(409, 'idempotency_conflict', 'action_id already has different roll arguments')
                return self.public(json.loads(prior['result']))
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
                else:
                    result = self.dice.rarity(row['luck'])
                results.append({'label': row['label'], 'kind': kind, 'result': result})
            receipt = {'action_id': action_id, 'results': results, 'rng': self.dice.source,
                       'created_at': datetime.now(timezone.utc).isoformat(), 'campaign_changed': False}
            records.insert(db, 'game_rolls_v1', {'owner': owner, 'action_id': action_id,
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
            return self.public(json.loads(row['result']), show_rolls)
