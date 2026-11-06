"""Copy a college's prefixed collections into its own MongoDB database.

Run from ``backend`` to inspect the proposed migration, then apply it:

    python migrate_tenant_to_database.py --institution-code KO11142SFE
    python migrate_tenant_to_database.py --institution-code KO11142SFE --apply

The script preserves the original collections and only changes the institute's
database pointer after every copied collection has been verified.
"""
from __future__ import annotations

import argparse
from copy import deepcopy

from pymongo import MongoClient

from app.core.config import settings
from app.core.database import (
    _safe_tenant_db_name,
    clear_cached_institution,
    ensure_indexes,
)
from app.core.docstore import DocStore


def _expected_document(document: dict, collection_name: str, institution, target_name: str) -> dict:
    expected = deepcopy(document)
    if collection_name == "institutions" and expected.get("code") == institution.code:
        expected["database_url"] = target_name
    return expected


def migrate_institution(control, client, institution, *, apply: bool) -> None:
    source_name = institution.database_url
    if not source_name:
        raise ValueError("The institution has no source database namespace")

    target_name = _safe_tenant_db_name(institution)
    control_name = settings.MONGODB_DB_PREFIX
    if target_name == control_name or target_name == source_name:
        raise ValueError("Source, target, and control databases must be distinct")

    control_database = client[control_name]
    source_prefix = f"{source_name}__"
    source_collections = sorted(
        name for name in control_database.list_collection_names()
        if name.startswith(source_prefix)
    )
    if not source_collections:
        raise ValueError("No source college collections were found; no data was changed")

    source_institution_collection = control_database[f"{source_prefix}institutions"]
    source_identity = source_institution_collection.find_one(
        {"_id": institution.id},
        {"_id": 1, "code": 1, "name": 1},
    )
    if (
        not source_identity
        or source_identity.get("code") != institution.code
        or source_identity.get("name") != institution.name
    ):
        raise ValueError("Source college identity does not match the institute registry")

    target_database = client[target_name]
    target_collections = target_database.list_collection_names()
    unexpected = sorted(set(target_collections) - {
        name[len(source_prefix):] for name in source_collections
    })
    if unexpected:
        raise ValueError(
            "Target database already contains unrelated collections: "
            + ", ".join(unexpected)
        )

    print(f"Institution: {institution.name} ({institution.code})")
    print(f"Source: {control_name} / {source_prefix}*")
    print(f"Target: {target_name} / normal collection names")
    print(f"Collections to copy: {len(source_collections)}")
    source_counts = {}
    for source_collection_name in source_collections:
        collection_name = source_collection_name[len(source_prefix):]
        count = control_database[source_collection_name].count_documents({})
        source_counts[collection_name] = count
        print(f"  {collection_name}: {count}")

    if not apply:
        print("Dry run only; no MongoDB records or settings were changed.")
        return

    tenant_store = DocStore(target_database, client=client)
    ensure_indexes(tenant_store)

    for source_collection_name in source_collections:
        collection_name = source_collection_name[len(source_prefix):]
        source_collection = control_database[source_collection_name]
        target_collection = target_database[collection_name]
        pending = []
        for document in source_collection.find({}):
            expected = _expected_document(
                document, collection_name, institution, target_name
            )
            existing = target_collection.find_one({"_id": document["_id"]})
            if existing is not None:
                if existing != expected:
                    raise ValueError(
                        f"Target conflict in {collection_name}; existing data differs"
                    )
                continue
            pending.append(expected)
            if len(pending) >= 500:
                target_collection.insert_many(pending, ordered=True)
                pending.clear()
        if pending:
            target_collection.insert_many(pending, ordered=True)

    for source_collection_name in source_collections:
        collection_name = source_collection_name[len(source_prefix):]
        source_collection = control_database[source_collection_name]
        target_collection = target_database[collection_name]
        source_count = source_counts[collection_name]
        if target_collection.count_documents({}) != source_count:
            raise RuntimeError(f"Record-count verification failed for {collection_name}")
        for source_document in source_collection.find({}):
            expected = _expected_document(
                source_document, collection_name, institution, target_name
            )
            if target_collection.find_one({"_id": source_document["_id"]}) != expected:
                raise RuntimeError(f"Document verification failed for {collection_name}")

    tenant_identity = target_database["institutions"].find_one(
        {"_id": institution.id, "code": institution.code, "name": institution.name}
    )
    if not tenant_identity:
        raise RuntimeError("The copied tenant institution identity could not be verified")

    control.update(institution, {"database_url": target_name})
    clear_cached_institution(institution.id)
    print("All copied collections and documents were verified.")
    print("The control registry now points to the new college database.")
    print("Original prefixed collections were retained.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution-code", required=True)
    parser.add_argument("--apply", action="store_true", help="copy data and update the institute database pointer")
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
        control = DocStore(client[settings.MONGODB_DB_PREFIX], client=client)
        institutions = control.find("institutions", {"code": args.institution_code})
        if len(institutions) != 1:
            raise ValueError("Expected exactly one institute with that code")
        migrate_institution(control, client, institutions[0], apply=args.apply)
    except Exception as exc:
        print(f"Migration stopped ({type(exc).__name__}); no credentials were printed.")
        return 1
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
