"""Typed document fa?ade over one Mongo database.

DocStore keeps the route-facing API stable while translating SQL-era string ids,
field names, and Python date/decimal values to BSON. Cascades are best-effort and
are not atomic unless an explicit Mongo transaction is used.
"""
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
from decimal import Decimal
import re
from typing import Any, Iterable, Iterator

from bson import Decimal128
from pymongo.errors import DuplicateKeyError

from app.core.schema import CASCADE_EDGES, COLLECTIONS


class Conflict(Exception):
    """A Mongo unique-index conflict, with the conflicting index name when available."""

    def __init__(self, index: str = ""):
        self.index = index
        super().__init__(f"Duplicate value violates index {index}" if index else "Duplicate value")


class MissingReference(Exception):
    """A referenced record does not exist in the selected institution database."""


class Doc(dict):
    """Dictionary document with attribute access and `_id`/`id` compatibility."""

    def __init__(self, data: dict[str, Any], *, collection: str | None = None, store=None):
        source = dict(data)
        doc_id = source.pop("_id", source.get("id", None))
        if doc_id is not None:
            source["id"] = str(doc_id)
        super().__init__(source)
        object.__setattr__(self, "_collection", collection)
        object.__setattr__(self, "_store", store)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self[name] = value


class UserDoc(Doc):
    """A user document with cached, per-document relationship lookups."""

    def __init__(self, data: dict[str, Any], *, collection: str | None = "users", store=None):
        super().__init__(data, collection=collection, store=store)
        object.__setattr__(self, "_lazy_cache", {})

    def _lazy(self, key: str, loader):
        cache = self._lazy_cache
        if key not in cache:
            cache[key] = loader()
        return cache[key]

    @property
    def full_name(self) -> str:
        return ' '.join(part for part in (self.get('first_name'), self.get('middle_name'), self.get('last_name')) if part)

    @property
    def role_names(self) -> list[str]:
        def load():
            if self._store is None or not self.id:
                return []
            assignments = self._store.find("user_role_assignments", {"user_id": self.id})
            roles = self._store.get_many("roles", [item.role_id for item in assignments if item.role_id])
            return [role.name for role in roles.values()]
        return self._lazy("role_names", load)

    @property
    def student_profile(self) -> Doc | None:
        return self._lazy("student_profile", lambda: self._profile("students"))

    @property
    def faculty_profile(self) -> Doc | None:
        return self._lazy("faculty_profile", lambda: self._profile("faculty_profiles"))

    @property
    def guardian_profile(self) -> Doc | None:
        return self._lazy("guardian_profile", lambda: self._profile("guardians"))

    @property
    def preferences(self) -> Doc | None:
        return self._lazy("preferences", lambda: self._store.find_one("user_preferences", {"user_id": self.id}) if self._store else None)

    def _profile(self, collection: str) -> Doc | None:
        if self._store is None or not self.id:
            return None
        return self._store.find_one(collection, {"user_id": self.id})


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _encode_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return Decimal128(value)
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    if isinstance(value, dict):
        return {str(key): _encode_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_encode_json(item) for item in value]
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    return value


def _decode_json(value: Any) -> Any:
    if isinstance(value, Decimal128):
        return value.to_decimal()
    if isinstance(value, dict):
        return {key: _decode_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_json(item) for item in value]
    return value


def _encode_typed(value: Any, type_tag: str | None) -> Any:
    if value is None or type_tag is None:
        return value
    if type_tag == "dec":
        return Decimal128(value if isinstance(value, Decimal) else Decimal(str(value)))
    if type_tag == "date":
        if isinstance(value, datetime):
            return _as_utc(value)
        if isinstance(value, date):
            return datetime.combine(value, time.min, tzinfo=timezone.utc)
    if type_tag == "dt" and isinstance(value, datetime):
        return _as_utc(value)
    if type_tag == "time" and isinstance(value, time):
        return value.isoformat(timespec="seconds")
    if type_tag == "json":
        return _encode_json(value)
    return value


def _decode_typed(value: Any, type_tag: str | None) -> Any:
    if value is None:
        return None
    if type_tag == "dec" and isinstance(value, Decimal128):
        return value.to_decimal()
    if type_tag == "date" and isinstance(value, datetime):
        return value.date()
    if type_tag == "dt" and isinstance(value, datetime):
        return _as_utc(value)
    if type_tag == "time" and isinstance(value, str):
        try:
            return time.fromisoformat(value)
        except ValueError:
            return value
    if type_tag == "json":
        return _decode_json(value)
    return value


def _mongo_filter(filter_value: dict | None, spec) -> dict:
    if not filter_value:
        return {}
    result: dict[str, Any] = {}
    for key, value in filter_value.items():
        if key == "$or" or key == "$and":
            result[key] = [_mongo_filter(item, spec) for item in value]
            continue
        field_name = "_id" if key == "id" else key
        tag = "str" if field_name == "_id" else spec.fields.get(key.split(".", 1)[0])
        if isinstance(value, dict) and any(str(k).startswith("$") for k in value):
            result[field_name] = {operator: [_encode_typed(item, tag) for item in operand] if operator in ("$in", "$nin", "$all") else _encode_typed(operand, tag) for operator, operand in value.items()}
        else:
            result[field_name] = _encode_typed(value, tag)
    return result


def _index_name(error: Exception) -> str:
    message = str(error)
    match = re.search(r"index:\s+([^\s]+)", message)
    return match.group(1) if match else ""


class DocStore:
    """Per-request handle for a single Mongo database; route API defined by t1."""

    def __init__(self, database, *, client=None, collection_prefix: str | None = None):
        self._database = database
        self._client = client or getattr(database, "client", None)
        self.name = database.name
        self.collection_prefix = collection_prefix
        self._session = None
        self._request_scope = False

    def _spec(self, coll: str):
        try:
            return COLLECTIONS[coll]
        except KeyError as exc:
            raise KeyError(f"Unknown collection: {coll}") from exc

    def _collection(self, coll: str):
        self._spec(coll)
        return self._database[self.physical_collection_name(coll)]

    def physical_collection_name(self, coll: str) -> str:
        self._spec(coll)
        return f"{self.collection_prefix}__{coll}" if self.collection_prefix else coll

    def _session_kw(self, *, write: bool = False) -> dict[str, Any]:
        if write and self._request_scope and self._session is None:
            if self._client is None:
                raise RuntimeError("Mongo client is unavailable for request transaction")
            self._session = self._client.start_session()
            self._session.start_transaction()
        return {"session": self._session} if self._session is not None else {}

    @contextmanager
    def request_scope(self) -> Iterator["DocStore"]:
        """Commit all request writes together, starting a transaction only on first write."""
        if self._request_scope:
            raise RuntimeError("Nested DocStore request scopes are not supported")
        self._request_scope = True
        try:
            yield self
            if self._session is not None:
                self._session.commit_transaction()
        except BaseException:
            if self._session is not None:
                self._session.abort_transaction()
            raise
        finally:
            session = self._session
            self._session = None
            self._request_scope = False
            if session is not None:
                session.end_session()

    def _decode(self, coll: str, raw: dict | None) -> Doc | None:
        if raw is None:
            return None
        spec = self._spec(coll)
        decoded = {}
        raw_id = raw.get("_id")
        for key, value in raw.items():
            if key == "_id":
                continue
            decoded[key] = _decode_typed(value, spec.fields.get(key))
        if raw_id is not None:
            decoded["id"] = str(raw_id)
        for key, value in spec.defaults.items():
            decoded.setdefault(key, value)
        for key in spec.nullable:
            decoded.setdefault(key, None)
        doc_type = UserDoc if coll == "users" else Doc
        return doc_type(decoded, collection=coll, store=self)

    def _encode_data(self, coll: str, data: dict) -> dict:
        spec = self._spec(coll)
        encoded: dict[str, Any] = {}
        for key, value in data.items():
            if key == "id":
                continue
            if key == "_id":
                encoded[key] = str(value)
            else:
                encoded[key] = _encode_typed(value, spec.fields.get(key))
        return encoded

    def _validate_references(self, coll: str, data: dict) -> None:
        for foreign_key in self._spec(coll).fks:
            value = data.get(foreign_key.field)
            if value is not None and self.get(foreign_key.collection, str(value)) is None:
                raise MissingReference(
                    f"{coll}.{foreign_key.field} references a missing {foreign_key.collection} record"
                )

    def get(self, coll: str, id: str) -> Doc | None:
        raw = self._collection(coll).find_one({"_id": str(id)}, **self._session_kw())
        return self._decode(coll, raw)

    def find_one(self, coll: str, filter: dict | None = None, *, sort: list[tuple[str, int]] | None = None) -> Doc | None:
        query = _mongo_filter(filter, self._spec(coll))
        cursor = self._collection(coll).find(query, **self._session_kw())
        if sort:
            cursor = cursor.sort([("_id" if key == "id" else key, direction) for key, direction in sort])
        return self._decode(coll, next(cursor.limit(1), None))

    def find(self, coll: str, filter: dict | None = None, *, sort: list[tuple[str, int]] | None = None, skip: int = 0, limit: int = 0) -> list[Doc]:
        query = _mongo_filter(filter, self._spec(coll))
        cursor = self._collection(coll).find(query, **self._session_kw())
        if sort:
            cursor = cursor.sort([("_id" if key == "id" else key, direction) for key, direction in sort])
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return [doc for raw in cursor if (doc := self._decode(coll, raw)) is not None]

    def count(self, coll: str, filter: dict | None = None) -> int:
        return self._collection(coll).count_documents(_mongo_filter(filter, self._spec(coll)), **self._session_kw())

    def exists(self, coll: str, filter: dict) -> bool:
        return self.find_one(coll, filter) is not None

    def get_many(self, coll: str, ids: Iterable[str]) -> dict[str, Doc]:
        requested = list(dict.fromkeys(str(item) for item in ids if item is not None))
        if not requested:
            return {}
        cursor = self._collection(coll).find({"_id": {"$in": requested}}, **self._session_kw())
        docs = [self._decode(coll, raw) for raw in cursor]
        return {doc.id: doc for doc in docs if doc is not None}

    def insert(self, coll: str, data: dict) -> Doc:
        spec = self._spec(coll)
        values = dict(data)
        identifier = str(values.pop("id", values.pop("_id", "")) or __import__("uuid").uuid4())
        now = datetime.now(timezone.utc)
        for key, value in spec.defaults.items():
            values.setdefault(key, value)
        for key in spec.nullable:
            values.setdefault(key, None)
        values.setdefault("created_at", now)
        values.setdefault("updated_at", now)
        self._validate_references(coll, values)
        encoded = self._encode_data(coll, values)
        encoded["_id"] = identifier
        try:
            self._collection(coll).insert_one(encoded, **self._session_kw(write=True))
        except DuplicateKeyError as exc:
            raise Conflict(_index_name(exc)) from exc
        return self.get(coll, identifier)

    def insert_many(self, coll: str, items: list[dict]) -> list[Doc]:
        return [self.insert(coll, item) for item in items]

    def update(self, target: Doc | str, changes: dict, *, coll: str | None = None) -> Doc:
        if isinstance(target, Doc):
            identifier = target.id
            coll = coll or target._collection
        else:
            identifier = str(target)
        if not coll:
            raise ValueError("coll is required when updating by id")
        self._spec(coll)
        update_values = {key: value for key, value in changes.items() if key not in ("id", "_id", "created_at")}
        update_values["updated_at"] = datetime.now(timezone.utc)
        self._validate_references(coll, update_values)
        encoded = self._encode_data(coll, update_values)
        try:
            self._collection(coll).update_one({"_id": str(identifier)}, {"$set": encoded}, **self._session_kw(write=True))
        except DuplicateKeyError as exc:
            raise Conflict(_index_name(exc)) from exc
        fresh = self.get(coll, str(identifier))
        if fresh is None:
            raise KeyError(f"Document not found in {coll}: {identifier}")
        if isinstance(target, Doc):
            target.clear()
            target.update(fresh)
            return target
        return fresh

    def update_many(self, coll: str, filter: dict, changes: dict) -> int:
        update_values = {key: value for key, value in changes.items() if key not in ("id", "_id", "created_at")}
        update_values.setdefault("updated_at", datetime.now(timezone.utc))
        self._validate_references(coll, update_values)
        try:
            result = self._collection(coll).update_many(
                _mongo_filter(filter, self._spec(coll)),
                {"$set": self._encode_data(coll, update_values)},
                **self._session_kw(write=True),
            )
        except DuplicateKeyError as exc:
            raise Conflict(_index_name(exc)) from exc
        return result.modified_count

    def increment(self, coll: str, id: str, field: str, amount: int = 1) -> None:
        self._spec(coll)
        self._collection(coll).update_one(
            {"_id": str(id)},
            {"$inc": {field: amount}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            **self._session_kw(write=True),
        )

    def delete(self, coll: str, id_or_doc: str | Doc) -> bool:
        identifier = id_or_doc.id if isinstance(id_or_doc, Doc) else str(id_or_doc)
        return self._delete_recursive(coll, identifier, set())

    def _delete_recursive(self, coll: str, identifier: str, visited: set[tuple[str, str]]) -> bool:
        key = (coll, str(identifier))
        if key in visited:
            return False
        visited.add(key)
        if self.get(coll, str(identifier)) is None:
            return False
        for child_coll, child_field, parent_coll, action in CASCADE_EDGES:
            if parent_coll != coll:
                continue
            children = self.find(child_coll, {child_field: str(identifier)})
            if action == "SET_NULL":
                if children:
                    self.update_many(child_coll, {child_field: str(identifier)}, {child_field: None})
            else:
                for child in children:
                    self._delete_recursive(child_coll, child.id, visited)
        result = self._collection(coll).delete_one({"_id": str(identifier)}, **self._session_kw(write=True))
        return result.deleted_count > 0

    def delete_many(self, coll: str, filter: dict) -> int:
        documents = self.find(coll, filter)
        return sum(1 for document in documents if self.delete(coll, document))

    @contextmanager
    def transaction(self) -> Iterator["DocStore"]:
        """Run operations in an explicit single-database Mongo transaction.

        Unsupported standalone servers/mocks raise rather than silently degrading.
        Tests that intentionally use mongomock replace this context manager explicitly.
        """
        if self._session is not None:
            raise RuntimeError("Nested DocStore transactions are not supported")
        if self._client is None:
            raise RuntimeError("Mongo client is unavailable for transaction")
        with self._client.start_session() as session:
            session.start_transaction()
            self._session = session
            try:
                yield self
                session.commit_transaction()
            except BaseException:
                try:
                    session.abort_transaction()
                finally:
                    raise
            finally:
                self._session = None
