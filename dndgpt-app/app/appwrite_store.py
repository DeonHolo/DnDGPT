"""Appwrite TablesDB transactions; rows are private to the server credential."""
from contextlib import contextmanager
import hashlib
import json
from urllib.parse import urlsplit
import uuid

import httpx

from . import records
from .engine import fail
from .storage import canonical

FIELDS = {"id": "record_id", "owner": "owner", "campaign_id": "campaign_id",
          "action_id": "action_id", "number": "number", "version": "version",
          "created_at": "created_at", "result": "completed", "rowid": "$createdAt"}


class AppwriteAPI:
    def __init__(self, endpoint, project_id, key, *, client=None):
        parsed = urlsplit(endpoint)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.query or parsed.fragment
                or parsed.username or parsed.password or not endpoint.endswith("/v1")):
            raise ValueError("Appwrite endpoint must be an HTTPS /v1 URL")
        if not project_id or not key:
            raise ValueError("Appwrite project and server credential required")
        self.endpoint = endpoint.rstrip("/")
        self.headers = {"X-Appwrite-Project": project_id, "X-Appwrite-Key": key,
                        "Content-Type": "application/json"}
        self.client = client or httpx.Client(timeout=15, follow_redirects=False)

    def call(self, method, path, **kwargs):
        try:
            response = self.client.request(method, self.endpoint + path,
                                           headers=self.headers, **kwargs)
        except httpx.HTTPError:
            fail(503, "storage_unavailable", "Hosted storage could not confirm the request; retry the same action_id")
        if response.status_code == 404:
            return None
        if response.status_code == 409:
            fail(409, "storage_conflict", "Concurrent save conflict; read state and retry the same action_id")
        if not response.is_success:
            fail(503, "storage_unavailable", "Hosted storage rejected the request")
        return response.json() if response.content else {}


class AppwriteStore:
    def __init__(self, api, database_id="dndgpt", table_id="records"):
        for value in (database_id, table_id):
            if not isinstance(value, str) or not value or len(value) > 36 or any(
                    c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in value):
                raise ValueError("Invalid Appwrite database/table ID")
        self.api = api
        self.path = "/tablesdb/" + database_id + "/tables/" + table_id

    def initialize(self):
        table = self.api.call("GET", self.path)
        if table is None or table.get("$permissions") or table.get("rowSecurity") is not True:
            raise ValueError("Hosted record table must exist with no client permissions")
        columns = {column["key"]: column for column in table.get("columns", [])}
        expected = set(FIELDS.values()) - {"$createdAt"} | {"kind", "payload", "guard"}
        if not expected <= set(columns) or any(columns[key].get("status") != "available" for key in expected):
            raise ValueError("Hosted record columns are not ready")

    @contextmanager
    def transaction(self):
        tx = self.api.call("POST", "/tablesdb/transactions", json={"ttl": 60})
        if not tx or "$id" not in tx:
            fail(503, "storage_unavailable", "Could not start hosted transaction")
        session = AppwriteSession(self, tx["$id"])
        try:
            yield session
            result = self.api.call("PATCH", "/tablesdb/transactions/" + session.id,
                                   json={"commit": True} if session.changed else {"rollback": True})
            if result is None:
                fail(503, "storage_unavailable", "Hosted transaction expired; retry the same action_id")
        except BaseException:
            try:
                self.api.call("PATCH", "/tablesdb/transactions/" + session.id, json={"rollback": True})
            except Exception:
                pass
            raise


class AppwriteSession:
    def __init__(self, store, transaction_id):
        self.store, self.id = store, transaction_id
        self.changed = False
        self.locked = {}

    @staticmethod
    def row_id(table, values):
        keys = records.KEYS[table]
        return hashlib.sha256(canonical([table, *[values[key] for key in keys]]).encode()).hexdigest()[:36]

    @staticmethod
    def metadata(table, row):
        return {"kind": table, "record_id": row.get("id", ""), "owner": row.get("owner", ""),
                "campaign_id": row.get("campaign_id", ""), "action_id": row.get("action_id", ""),
                "number": row.get("number", 0), "version": row.get("version", 0),
                "created_at": row.get("created_at", 0), "completed": row.get("result") is not None,
                "payload": canonical(row), "guard": uuid.uuid4().hex}

    @staticmethod
    def query(method, attribute=None, values=None):
        return canonical({"method": method, **({"attribute": attribute} if attribute else {}),
                          **({"values": values} if values is not None else {})})

    @staticmethod
    def decode(row):
        data = row.get("data", row)
        if not isinstance(data, dict) or not isinstance(data.get("payload"), str):
            fail(503, "storage_integrity", "Hosted record has an invalid payload")
        value = json.loads(data["payload"])
        if not isinstance(value, dict):
            fail(503, "storage_integrity", "Hosted record is not an object")
        return value

    def find_records(self, table, where, *, order=None, descending=False, limit=None,
                     minimum=None, maximum=None):
        if table not in records.KEYS:
            raise ValueError("Unknown record table")
        queries = [self.query("equal", "kind", [table])]
        for field, value in where.items():
            queries.append(self.query("equal", FIELDS[field],
                                      [value is not None] if field == "result" else [value]))
        for method, fields in (("greaterThan", minimum or {}), ("lessThanEqual", maximum or {})):
            queries += [self.query(method, FIELDS[key], [value]) for key, value in fields.items()]
        if order:
            queries.append(self.query("orderDesc" if descending else "orderAsc", FIELDS[order]))
        result, cursor = [], None
        while limit is None or len(result) < limit:
            page_size = min(100, limit - len(result)) if limit else 100
            page_queries = [*queries, self.query("limit", values=[page_size])]
            if cursor:
                page_queries.append(self.query("cursorAfter", values=[cursor]))
            page = self.store.api.call("GET", self.store.path + "/rows", params={
                "queries[]": page_queries, "transactionId": self.id, "total": "false"})
            if page is None:
                fail(503, "storage_unavailable", "Hosted record table is unavailable")
            rows = page["rows"]
            result.extend(self.decode(row) for row in rows)
            if len(rows) < page_size:
                break
            cursor = rows[-1]["$id"]
        return result

    def get_record(self, table, where):
        if set(records.KEYS[table]) <= where.keys():
            key = self.row_id(table, where)
            row = self.locked.get(key) or self.store.api.call(
                "GET", self.store.path + "/rows/" + key, params={"transactionId": self.id})
        else:
            found = self.find_records(table, where, limit=1)
            if not found:
                return None
            key = self.row_id(table, found[0])
            row = self.locked.get(key)
            if row is None:
                row = self.store.api.call("GET", self.store.path + "/rows/" + key,
                                          params={"transactionId": self.id})
        if row is None:
            return None
        decoded = self.decode(row)
        if any(decoded.get(field) != value for field, value in where.items()):
            return None
        if key not in self.locked:
            # Stage before using the returned snapshot, so a competing writer
            # cannot slip between our version check and the eventual update.
            row = self.store.api.call("PATCH", self.store.path + "/rows/" + key,
                                      json={"data": {"guard": uuid.uuid4().hex}, "transactionId": self.id})
            if row is None:
                fail(409, "storage_conflict", "Record changed during the read")
            self.locked[key] = row
            decoded = self.decode(row)
            if any(decoded.get(field) != value for field, value in where.items()):
                return None
        return decoded

    def insert_record(self, table, values):
        key = self.row_id(table, values)
        row = self.store.api.call("POST", self.store.path + "/rows", json={
            "rowId": key, "data": self.metadata(table, values), "permissions": [], "transactionId": self.id})
        if row is None:
            fail(503, "storage_unavailable", "Hosted record could not be created")
        self.locked[key] = row
        self.changed = True

    def update_record(self, table, where, values):
        prior = self.get_record(table, where)
        if prior is None:
            return
        merged = {**prior, **values}
        key = self.row_id(table, prior)
        if self.row_id(table, merged) != key:
            raise ValueError("Record identity cannot change")
        row = self.store.api.call("PATCH", self.store.path + "/rows/" + key,
                                  json={"data": self.metadata(table, merged), "transactionId": self.id})
        if row is None:
            fail(409, "storage_conflict", "Record changed during the update")
        self.locked[key] = row
        self.changed = True
