"""Read-only integrity audit of chat-led snapshots and current records."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from app.storage import canonical


def audit(path, campaign_id=None):
    results = []
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT id,version,data FROM campaigns_v1'):
            if campaign_id and row['id'] != campaign_id:
                continue
            current = json.loads(row['data'])
            if current.get('mode') != 'chat':
                continue
            versions = db.execute('SELECT version,data FROM chat_versions_v1 WHERE campaign_id=? ORDER BY version', (row['id'],)).fetchall()
            events = db.execute('SELECT * FROM events_v1 WHERE campaign_id=? ORDER BY number', (row['id'],)).fetchall()
            valid = len(versions) == len(events) == current['version'] == row['version']
            previous = '0' * 64
            for index, (saved, event_row) in enumerate(zip(versions, events), 1):
                state = json.loads(saved['data'])
                event = json.loads(event_row['event'])
                state_digest = hashlib.sha256(canonical({key: value for key, value in state.items() if key != 'last_event'}).encode()).hexdigest()
                digest = hashlib.sha256((previous + event_row['event']).encode()).hexdigest()
                valid &= saved['version'] == state['version'] == event_row['number'] == index
                valid &= event['state_sha256'] == state_digest and state['last_event'] == event
                valid &= event_row['previous_hash'] == previous and event_row['hash'] == digest
                previous = digest
            valid &= bool(versions) and versions[-1]['data'] == row['data']
            results.append({'id': row['id'], 'version': row['version'], 'snapshots': len(versions),
                            'events': len(events), 'valid': bool(valid)})
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('--campaign-id')
    args = parser.parse_args()
    results = audit(args.database, args.campaign_id)
    if args.campaign_id and not results:
        parser.error('Requested chat-led record was not found')
    print(json.dumps({'records': results, 'all_valid': all(row['valid'] for row in results)}))
    raise SystemExit(0 if all(row['valid'] for row in results) else 1)
