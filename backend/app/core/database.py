"""MongoDB control/tenant routing and collection bootstrap."""
from hashlib import sha1
import re
from threading import RLock
import time
from typing import Generator

from fastapi import Request
from pymongo import ASCENDING
from pymongo.errors import CollectionInvalid
from sqlalchemy.orm import declarative_base

from app.core.config import settings
from app.core.default_subjects import ensure_default_subjects
from app.core.docstore import DocStore
from app.core.mongo import get_mongo_client
from app.core.schema import COLLECTIONS

_ATLAS_DB_NAME_LIMIT = 38
_tenant_stores: dict[tuple[str, str | None], DocStore] = {}
_indexed_databases: set[tuple[str, str | None]] = set()
_institution_db_cache: dict[str, tuple[str | None, float]] = {}
_cache_lock = RLock()

# Retained as legacy schema metadata for Alembic and source-database tooling.
Base = declarative_base()


def clear_store_caches() -> None:
    """Clear per-process handles/caches; primarily useful for isolated tests."""
    with _cache_lock:
        _tenant_stores.clear()
        _indexed_databases.clear()
        _institution_db_cache.clear()


def _prefix() -> str:
    prefix = settings.MONGODB_DB_PREFIX
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,30}", prefix or ""):
        raise ValueError("MONGODB_DB_PREFIX must contain 1-30 ASCII letters, digits, '_' or '-'")
    return prefix


def _validate_database_name(name: str) -> str:
    # Never interpret a stored legacy PostgreSQL URL or a Mongo URI as a database name.
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,38}", name):
        raise ValueError("Institution database_url must contain a Mongo database name, not a connection URI")
    return name


def _store_for_name(name: str, collection_prefix: str | None = None) -> DocStore:
    name = _validate_database_name(name)
    cache_key = (name, collection_prefix)
    with _cache_lock:
        store = _tenant_stores.get(cache_key)
        if store is None:
            client = get_mongo_client()
            store = DocStore(client[name], client=client, collection_prefix=collection_prefix)
            _tenant_stores[cache_key] = store
    if cache_key not in _indexed_databases:
        ensure_indexes(store)
    return DocStore(store._database, client=store._client, collection_prefix=collection_prefix)


def get_control_store() -> DocStore:
    return _store_for_name(_prefix())


def get_tenant_store(name: str | None) -> DocStore:
    """Return a college-prefixed store in the shared Mongo database."""
    if not name:
        return get_control_store()
    return _store_for_name(_prefix(), name)


def ensure_indexes(store: DocStore) -> None:
    """Create all 39 same-named collections and declared indexes idempotently."""
    with _cache_lock:
        key = (store.name, store.collection_prefix)
        if key in _indexed_databases:
            return
        existing = set(store._database.list_collection_names())
        for name, spec in COLLECTIONS.items():
            physical_name = store.physical_collection_name(name)
            if physical_name not in existing:
                try:
                    store._database.create_collection(physical_name)
                except CollectionInvalid:
                    # Another worker may have won the create race.
                    if physical_name not in store._database.list_collection_names():
                        raise
            collection = store._database[physical_name]
            for index in spec.indexes:
                keys = [(key, ASCENDING) for key in index.fields]
                options = {"unique": index.unique, "name": index.name}
                if index.partial_filter is not None:
                    options["partialFilterExpression"] = index.partial_filter
                collection.create_index(keys, **options)
        _indexed_databases.add(key)


_NAME_FILLER_WORDS = {"of", "the", "and", "for", "at", "in"}
_RESERVED_DATABASE_NAMES = {"admin", "local", "config"}


def _safe_tenant_db_name(institution, *, force_suffix: bool = False) -> str:
    """Name an institute's database after the college, e.g. Chate_Junior_College_Science_Kolhapur.

    Atlas limits database names to 38 bytes, so filler words are dropped first and a short
    id-derived suffix is appended only if the name is still too long, empty or reserved.
    """
    institution_id = _read(institution, "id", "")
    title = str(_read(institution, "name", "") or _read(institution, "slug", "") or "")
    words = re.findall(r"[A-Za-z0-9]+", title)
    base = "_".join(words)
    if len(base) > _ATLAS_DB_NAME_LIMIT:
        base = "_".join(word for word in words if word.lower() not in _NAME_FILLER_WORDS)
    control = _prefix().lower()
    needs_suffix = (
        force_suffix
        or not base
        or len(base) > _ATLAS_DB_NAME_LIMIT
        or base.lower() in _RESERVED_DATABASE_NAMES | {control}
    )
    if needs_suffix:
        suffix = "_" + sha1(str(institution_id).encode("utf-8")).hexdigest()[:6]
        base = (base or "College")[:_ATLAS_DB_NAME_LIMIT - len(suffix)].rstrip("_") + suffix
    return _validate_database_name(base)


def _read(value, key: str, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _institution_data(institution, db_name: str) -> dict:
    fields = (
        "id", "slug", "name", "code", "status", "address", "city", "state",
        "pincode", "phone", "email", "logo_url", "institution_type",
    )
    return {key: _read(institution, key) for key in fields if _read(institution, key) is not None} | {"database_url": db_name}


def provision_tenant_database(institution, principal_email: str | None = None,
                              principal_password: str | None = None,
                              principal_first_name: str = "Institution",
                              principal_middle_name: str | None = None,
                              principal_last_name: str = "Principal") -> str:
    """Create and bootstrap an isolated college namespace in the shared database."""
    name = _safe_tenant_db_name(institution)
    client = get_mongo_client()
    shared_db = client[_prefix()]
    if any(collection.startswith(f"{name}__") for collection in shared_db.list_collection_names()):
        name = _safe_tenant_db_name(institution, force_suffix=True)
    clear_cached_institution(_read(institution, "id", ""))
    try:
        store = get_tenant_store(name)
        store.insert("institutions", _institution_data(institution, name))
        store.insert("institution_settings", {
            "institution_id": str(_read(institution, "id")),
            "institution_type": _read(institution, "institution_type", "OTHER") or "OTHER",
        })
        role_names = ("SUPER_ADMIN", "PRINCIPAL", "FACULTY", "STUDENT", "PARENT", "OFFICE_STAFF")
        roles = {role_name: store.insert("roles", {
            "name": role_name,
            "description": f"{role_name} role permissions",
        }) for role_name in role_names}
        ensure_default_subjects(store, str(_read(institution, "id")))
        if principal_email and principal_password:
            from app.core.security import get_password_hash
            principal = store.insert("users", {
                "institution_id": str(_read(institution, "id")),
                "username": principal_email.split("@", 1)[0],
                "email": principal_email,
                "password_hash": get_password_hash(principal_password),
                "first_name": principal_first_name,
                "middle_name": principal_middle_name,
                "last_name": principal_last_name,
                "is_active": True,
                "is_verified": True,
            })
            store.insert("user_role_assignments", {
                "user_id": principal.id,
                "role_id": roles["PRINCIPAL"].id,
                "institution_id": str(_read(institution, "id")),
            })
        return name
    except Exception:
        for collection in shared_db.list_collection_names():
            if collection.startswith(f"{name}__"):
                shared_db.drop_collection(collection)
        with _cache_lock:
            _tenant_stores.pop((_prefix(), name), None)
            _indexed_databases.discard((_prefix(), name))
        raise


def clear_cached_institution(institution_id: str) -> None:
    with _cache_lock:
        _institution_db_cache.pop(str(institution_id), None)


def invalidate_institution_cache(institution_id: str) -> None:
    """Public invalidation hook for institution provisioning/update routes."""
    clear_cached_institution(institution_id)


def _institution_database_name(institution_id: str, control: DocStore) -> str | None:
    now = time.monotonic()
    with _cache_lock:
        cached = _institution_db_cache.get(institution_id)
        if cached and cached[1] > now:
            return cached[0]
    institution = control.find_one("institutions", {"id": institution_id})
    name = institution.database_url if institution else None
    with _cache_lock:
        _institution_db_cache[institution_id] = (name, now + 60.0)
    return name


def get_db(request: Request) -> Generator[DocStore, None, None]:
    """Yield control DB or the institution DB selected by X-Institution-ID."""
    control = get_control_store()
    institution_id = request.headers.get("X-Institution-ID")
    if institution_id:
        database_name = _institution_database_name(institution_id, control)
        store = get_tenant_store(database_name)
    else:
        store = control
    with store.request_scope():
        yield store
