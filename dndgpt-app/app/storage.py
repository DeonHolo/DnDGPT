"""SQLite persistence, isolated from framework and game mechanics."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


class Store:
    def __init__(self, path):
        self.path = Path(path)

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
                INSERT OR IGNORE INTO schema_version VALUES (1);
                CREATE TABLE IF NOT EXISTS campaigns_v1 (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    version INTEGER NOT NULL, data TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS campaign_owner ON campaigns_v1(owner);
                CREATE TABLE IF NOT EXISTS proposals_v1 (
                    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, owner TEXT NOT NULL,
                    action_id TEXT NOT NULL, request TEXT NOT NULL, preview TEXT NOT NULL,
                    approval_token TEXT NOT NULL, created_at REAL NOT NULL,
                    result TEXT, UNIQUE(campaign_id, action_id),
                    FOREIGN KEY(campaign_id) REFERENCES campaigns_v1(id));
                CREATE TABLE IF NOT EXISTS events_v1 (
                    campaign_id TEXT NOT NULL, number INTEGER NOT NULL,
                    event TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL,
                    PRIMARY KEY(campaign_id, number),
                    FOREIGN KEY(campaign_id) REFERENCES campaigns_v1(id));
                CREATE TABLE IF NOT EXISTS creations_v1 (
                    owner TEXT NOT NULL, action_id TEXT NOT NULL, request TEXT NOT NULL,
                    result TEXT NOT NULL, campaign_id TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(owner, action_id));
                CREATE TABLE IF NOT EXISTS ui_preferences_v1 (
                    owner TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS game_rolls_v1 (
                    owner TEXT NOT NULL, action_id TEXT NOT NULL,
                    request TEXT NOT NULL, result TEXT NOT NULL,
                    campaign_id TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(owner, action_id));
                CREATE TABLE IF NOT EXISTS campaign_deletions_v1 (
                    owner TEXT NOT NULL, campaign_id TEXT NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY(owner, campaign_id));
                CREATE TABLE IF NOT EXISTS chat_updates_v1 (
                    campaign_id TEXT NOT NULL, action_id TEXT NOT NULL,
                    request TEXT NOT NULL, result TEXT NOT NULL,
                    PRIMARY KEY(campaign_id, action_id),
                    FOREIGN KEY(campaign_id) REFERENCES campaigns_v1(id));
                CREATE TABLE IF NOT EXISTS gallery_entries_v1 (
                    owner TEXT NOT NULL, id TEXT NOT NULL, campaign_id TEXT NOT NULL,
                    created_at REAL NOT NULL, data TEXT NOT NULL, PRIMARY KEY(owner,id));
                CREATE INDEX IF NOT EXISTS gallery_campaign ON gallery_entries_v1(owner,campaign_id);
                CREATE TABLE IF NOT EXISTS gallery_assets_v1 (
                    owner TEXT NOT NULL, id TEXT NOT NULL, campaign_id TEXT NOT NULL,
                    data TEXT NOT NULL, PRIMARY KEY(owner,id));
                CREATE TABLE IF NOT EXISTS gallery_actions_v1 (
                    owner TEXT NOT NULL, action_id TEXT NOT NULL, campaign_id TEXT NOT NULL,
                    request TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(owner,action_id));
                CREATE TABLE IF NOT EXISTS chat_versions_v1 (
                    campaign_id TEXT NOT NULL, version INTEGER NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY(campaign_id, version),
                    FOREIGN KEY(campaign_id) REFERENCES campaigns_v1(id));
                CREATE TABLE IF NOT EXISTS creation_drafts_v1 (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL,
                    version INTEGER NOT NULL, data TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS creation_draft_owner ON creation_drafts_v1(owner);
                CREATE TABLE IF NOT EXISTS creation_proposals_v1 (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, draft_id TEXT NOT NULL,
                    action_id TEXT NOT NULL, expected_version INTEGER NOT NULL,
                    request TEXT NOT NULL, preview TEXT NOT NULL,
                    approval_token TEXT NOT NULL, created_at REAL NOT NULL,
                    result TEXT, UNIQUE(owner, action_id));
                CREATE TABLE IF NOT EXISTS creation_events_v1 (
                    draft_id TEXT NOT NULL, number INTEGER NOT NULL,
                    event TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL,
                    PRIMARY KEY(draft_id, number),
                    FOREIGN KEY(draft_id) REFERENCES creation_drafts_v1(id));
            """)
            for table in ("creations_v1", "game_rolls_v1"):
                columns = {row[1] for row in db.execute("PRAGMA table_info(" + table + ")")}
                if "campaign_id" not in columns:
                    db.execute("ALTER TABLE " + table +
                               " ADD COLUMN campaign_id TEXT NOT NULL DEFAULT ''")
            db.execute("CREATE INDEX IF NOT EXISTS creations_campaign ON creations_v1(owner, campaign_id)")
            db.execute("CREATE INDEX IF NOT EXISTS game_rolls_campaign ON game_rolls_v1(owner, campaign_id)")

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=20, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
