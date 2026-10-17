"""Small record operations shared by SQLite and hosted persistence."""
import re


KEYS = {
    "campaigns_v1": ("id",),
    "proposals_v1": ("campaign_id", "action_id"),
    "events_v1": ("campaign_id", "number"),
    "creations_v1": ("owner", "action_id"),
    "ui_preferences_v1": ("owner",),
    "game_rolls_v1": ("owner", "action_id"),
    "campaign_deletions_v1": ("owner", "campaign_id"),
    "chat_updates_v1": ("campaign_id", "action_id"),
    "chat_versions_v1": ("campaign_id", "version"),
}


def name(value):
    if not re.fullmatch(r"[a-z_][a-z_0-9]*", value):
        raise ValueError("Invalid persistence identifier")
    return value


def predicate(where, minimum=None, maximum=None):
    clauses, params = [], []
    for key, value in where.items():
        clauses.append(name(key) + (" IS NULL" if value is None else "=?"))
        if value is not None:
            params.append(value)
    for comparison, fields in ((">", minimum or {}), ("<=", maximum or {})):
        for key, value in fields.items():
            clauses.append(name(key) + comparison + "?")
            params.append(value)
    return " AND ".join(clauses) or "1=1", params


def find(db, table, where, *, order=None, descending=False, limit=None,
         minimum=None, maximum=None):
    if table not in KEYS:
        raise ValueError("Unknown record table")
    if hasattr(db, "find_records"):
        return db.find_records(table, where, order=order, descending=descending,
                               limit=limit, minimum=minimum, maximum=maximum)
    clause, params = predicate(where, minimum, maximum)
    sql = "SELECT * FROM " + table + " WHERE " + clause
    if order:
        sql += " ORDER BY " + name(order) + (" DESC" if descending else " ASC")
    if limit is not None:
        if type(limit) is not int or limit < 1:
            raise ValueError("Invalid record limit")
        sql += " LIMIT ?"
        params.append(limit)
    return [dict(row) for row in db.execute(sql, params).fetchall()]


def get(db, table, where):
    if hasattr(db, "get_record"):
        return db.get_record(table, where)
    rows = find(db, table, where, limit=1)
    return rows[0] if rows else None


def insert(db, table, values):
    if hasattr(db, "insert_record"):
        return db.insert_record(table, values)
    if table not in KEYS:
        raise ValueError("Unknown record table")
    columns = ",".join(name(key) for key in values)
    db.execute("INSERT INTO " + table + " (" + columns + ") VALUES (" +
               ",".join("?" for _ in values) + ")", list(values.values()))


def update(db, table, where, values):
    if hasattr(db, "update_record"):
        return db.update_record(table, where, values)
    if table not in KEYS or not where:
        raise ValueError("Unknown table or unbounded record update")
    clause, params = predicate(where)
    db.execute("UPDATE " + table + " SET " + ",".join(name(key) + "=?" for key in values) +
               " WHERE " + clause, [*values.values(), *params])


def delete(db, table, where):
    if table not in KEYS or not set(KEYS[table]) <= where.keys():
        raise ValueError("Unknown table or incomplete record identity")
    if hasattr(db, "delete_record"):
        return db.delete_record(table, where)
    clause, params = predicate(where)
    cursor = db.execute("DELETE FROM " + table + " WHERE " + clause, params)
    return cursor.rowcount


def upsert(db, table, where, values):
    if get(db, table, where) is None:
        insert(db, table, {**where, **values})
    else:
        update(db, table, where, values)
