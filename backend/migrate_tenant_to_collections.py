"""Copy a college database into named collections in the tenant data database.

Run from ``backend`` to inspect the proposed copy, then apply it:

    python migrate_tenant_to_collections.py --institution-code KO11142SFE
    python migrate_tenant_to_collections.py --institution-code KO11142SFE --apply

The source college database is retained. Application routing uses the new
collections only after every source document has been verified.
"""
from __future__ import annotations

import argparse

from pymongo import MongoClient

from app.core.config import settings
from app.core.database import (
    _safe_tenant_db_name,
    _tenant_collections_database,
    clear_cached_institution,
    get_control_store,
    get_tenant_store,
)
from app.core.docstore import DocStore
from app.core.schema import COLLECTIONS


def migrate_institution(control, client, institution, *, apply: bool) -> None:
    source_name = institution.database_url
    target_database_name = _tenant_collections_database()
    collection_prefix = _safe_tenant_db_name(institution)
    if source_name != collection_prefix:
        raise ValueError("The registered tenant name does not match the college name")
    if source_name in {settings.MONGODB_DB_PREFIX, target_database_name}:
        raise ValueError("Source, control, and target databases must be distinct")

    source_database = client[source_name]
    target_database = client[target_database_name]
    expected_sources = set(COLLECTIONS)
    source_names = {
        name for name in source_database.list_collection_names()
        if not name.startswith("system.")
    }
    if source_names != expected_sources:
        missing = sorted(expected_sources - source_names)
        unexpected = sorted(source_names - expected_sources)
        raise ValueError(
            f"Source collection layout mismatch; missing={missing}, unexpected={unexpected}"
        )

    source_identity = source_database["institutions"].find_one(
        {"_id": institution.id},
        {"_id": 1, "code": 1, "name": 1},
    )
    if (
        not source_identity
        or source_identity.get("code") != institution.code
        or source_identity.get("name") != institution.name
    ):
        raise ValueError("Source college identity does not match the control registry")

    prefix = f"{collection_prefix}__"
    target_prefix_names = {
        name for name in target_database.list_collection_names()
        if name.startswith(prefix)
    }
    allowed_target_names = {f"{prefix}{name}" for name in COLLECTIONS}
    unexpected_target_names = sorted(target_prefix_names - allowed_target_names)
    if unexpected_target_names:
        raise ValueError(
            "Target prefix contains unknown collections: "
            + ", ".join(unexpected_target_names)
        )

    source_counts = {
        name: source_database[name].count_documents({})
        for name in sorted(COLLECTIONS)
    }
    print(f"Institution: {institution.name} ({institution.code})")
    print(f"Source database: {source_name}")
    print(f"Target database: {target_database_name}")
    print(f"Collection prefix: {collection_prefix}__")
    print(f"Collections to copy: {len(source_counts)}")
    for name, count in source_counts.items():
        print(f"  {name}: {count}")

    if not apply:
        print("Dry run only; no MongoDB records were changed.")
        return

    target = DocStore(
        target_database,
        client=client,
        collection_prefix=collection_prefix,
    )
    from app.core.database import ensure_indexes
    ensure_indexes(target)

    for name in sorted(COLLECTIONS):
        source_collection = source_database[name]
        target_collection = target._collection(name)
        pending = []
        for document in source_collection.find({}):
            existing = target_collection.find_one({"_id": document["_id"]})
            if existing is not None:
                if existing != document:
                    raise ValueError(
                        f"Target conflict in {name}; existing document differs"
                    )
                continue
            pending.append(document)
            if len(pending) >= 500:
                target_collection.insert_many(pending, ordered=True)
                pending.clear()
        if pending:
            target_collection.insert_many(pending, ordered=True)

    for name in sorted(COLLECTIONS):
        source_collection = source_database[name]
        target_collection = target._collection(name)
        if target_collection.count_documents({}) != source_counts[name]:
            raise RuntimeError(f"Record-count verification failed for {name}")
        for document in source_collection.find({}):
            if target_collection.find_one({"_id": document["_id"]}) != document:
                raise RuntimeError(f"Document verification failed for {name}")

    copied_identity = target._collection("institutions").find_one(
        {"_id": institution.id, "code": institution.code, "name": institution.name}
    )
    if not copied_identity:
        raise RuntimeError("The copied tenant institution identity could not be verified")

    clear_cached_institution(institution.id)
    routed = get_tenant_store(institution.database_url)
    if (
        routed.name != target_database_name
        or routed.collection_prefix != collection_prefix
    ):
        raise RuntimeError("Application tenant routing did not select the copied collections")

    print("All copied collections and documents were verified.")
    print("Application routing now selects the college-prefixed collections.")
    print("The original college database was retained.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution-code", required=True)
    parser.add_argument("--apply", action="store_true", help="copy and verify all college records")
    args = parser.parse_args()

    if args.apply and (
        not settings.MONGODB_URI
        or not settings.MONGODB_URI.startswith(("mongodb://", "mongodb+srv://"))
    ):
        parser.error("Configure MONGODB_URI locally before applying the migration")

    client = MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        uuidRepresentation="standard",
        tz_aware=True,
    )
    try:
        client.admin.command("ping")
        control = get_control_store()
        institutions = control.find("institutions", {"code": args.institution_code})
        if len(institutions) != 1:
            raise ValueError("Expected exactly one institute with that code")
        migrate_institution(control, client, institutions[0], apply=args.apply)
    except Exception as exc:
        print(f"Migration stopped ({type(exc).__name__}); credentials were not printed.")
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
