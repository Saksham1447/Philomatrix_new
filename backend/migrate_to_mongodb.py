"""Copy the legacy relational database into MongoDB without overwriting data.

Run from ``backend`` with ``LEGACY_DATABASE_URL`` and ``MONGODB_URI`` set:

    python migrate_to_mongodb.py
    python migrate_to_mongodb.py --apply

The default is a read-only dry run. The migration uses the original SQL table
names as Mongo collection names and preserves string IDs and field names.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

from bson import BSON
from bson.codec_options import CodecOptions
from pymongo import MongoClient
from sqlalchemy import MetaData, Table, create_engine, func, inspect, select
from sqlalchemy.engine import Engine, make_url

from app.core.config import settings
from app.core.database import _safe_tenant_db_name, ensure_indexes
from app.core.docstore import DocStore
from app.core.schema import COLLECTIONS


@dataclass
class SourcePlan:
    label: str
    engine: Engine
    target_name: str
    tenant_id: str | None = None


def _normalized_source_url(raw_url: str) -> str:
    url = make_url(raw_url)
    if url.drivername == "postgres":
        url = url.set(drivername="postgresql+psycopg2")
    elif url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg2")
    elif url.drivername == "sqlite":
        database = url.database
        if database and database != ":memory:" and not Path(database).is_absolute():
            database = str((Path(__file__).resolve().parent / database).resolve())
            url = url.set(database=database)
    else:
        raise ValueError("Legacy source must be SQLite or PostgreSQL")
    return url.render_as_string(hide_password=False)


def _new_engine(raw_url: str) -> Engine:
    normalized = _normalized_source_url(raw_url)
    url = make_url(normalized)
    if (
        url.drivername.startswith("sqlite")
        and url.database
        and url.database != ":memory:"
        and not Path(url.database).is_file()
    ):
        raise FileNotFoundError("A configured legacy SQLite database file is unavailable")
    return create_engine(normalized, pool_pre_ping=True)


def _table_map(engine: Engine) -> dict[str, Table]:
    metadata = MetaData()
    names = set(inspect(engine).get_table_names())
    return {
        name: Table(name, metadata, autoload_with=engine)
        for name in COLLECTIONS
        if name in names
    }


def _source_institutions(engine: Engine) -> list[dict[str, Any]]:
    names = set(inspect(engine).get_table_names())
    if "institutions" not in names:
        return []
    metadata = MetaData()
    table = Table("institutions", metadata, autoload_with=engine)
    if not {"id", "slug"}.issubset(table.c.keys()):
        raise ValueError("Legacy institutions table is missing its ID or slug column")
    columns = [table.c.id, table.c.slug]
    for optional in ("name", "database_url"):
        if optional in table.c:
            columns.append(table.c[optional])
    with engine.connect() as connection:
        return [
            dict(row)
            for row in connection.execute(select(*columns)).mappings()
        ]


def _build_plans(source_url: str, control_target: str) -> tuple[list[SourcePlan], dict[str, str]]:
    root_engine = _new_engine(source_url)
    plans = [SourcePlan("control", root_engine, control_target)]
    tenant_targets: dict[str, str] = {}
    root_normalized = _normalized_source_url(source_url)
    root_url = make_url(root_normalized)
    tenant_sqlite_root = (Path(__file__).resolve().parent / "tenant_data").resolve()

    for institution in _source_institutions(root_engine):
        legacy_url = institution.get("database_url")
        if not legacy_url:
            continue
        normalized = _normalized_source_url(str(legacy_url))
        if normalized == root_normalized:
            continue
        tenant_url = make_url(normalized)
        if tenant_url.drivername.startswith("sqlite"):
            database_path = Path(tenant_url.database or "").resolve()
            if not database_path.is_relative_to(tenant_sqlite_root):
                raise ValueError("Institution SQLite sources must be inside backend/tenant_data")
        elif (
            tenant_url.host != root_url.host
            or tenant_url.port != root_url.port
        ):
            raise ValueError("Institution PostgreSQL sources must use the configured legacy server")
        institution_id = str(institution["id"])
        target_name = _safe_tenant_db_name(institution)
        tenant_targets[institution_id] = target_name
        tenant_engine = _new_engine(normalized)
        plans.append(SourcePlan(f"tenant:{institution_id}", tenant_engine, target_name, institution_id))
    return plans, tenant_targets


def _tables_in_plan(plan: SourcePlan) -> dict[str, Table]:
    return _table_map(plan.engine)


def _document_for_target(
    store: DocStore,
    collection: str,
    row: dict[str, Any],
    tenant_targets: dict[str, str],
    plan: SourcePlan,
) -> dict[str, Any]:
    source = dict(row)
    identifier = source.pop("id", None)
    if identifier is None:
        raise ValueError(f"Source table {collection} has a row without an ID")
    identifier = str(identifier)

    if collection == "institutions":
        institution_id = identifier
        if plan.tenant_id:
            source["database_url"] = plan.target_name
        elif institution_id in tenant_targets:
            source["database_url"] = tenant_targets[institution_id]
        elif "database_url" in source:
            source["database_url"] = None

    document = store._encode_data(collection, source)
    document["_id"] = identifier
    codec_options = CodecOptions(tz_aware=True, tzinfo=timezone.utc)
    return BSON(BSON.encode(document)).decode(codec_options=codec_options)


def _preflight(plans: list[SourcePlan], tenant_targets: dict[str, str], control_target: str, client) -> None:
    for plan in plans:
        store = DocStore(
            client[control_target],
            client=client,
            collection_prefix=None if not plan.tenant_id else plan.target_name,
        )
        ensure_indexes(store)
        tables = _tables_in_plan(plan)
        for collection, table in tables.items():
            target = store._collection(collection)
            with plan.engine.connect().execution_options(stream_results=True) as connection:
                for row in connection.execute(select(table)).mappings():
                    expected = _document_for_target(
                        store, collection, dict(row), tenant_targets, plan
                    )
                    existing = target.find_one({"_id": expected["_id"]})
                    if existing is not None and existing != expected:
                        raise ValueError(
                            f"Target conflict in {plan.label}.{collection}; "
                            "existing document differs, so no records were overwritten"
                        )


def _copy(
    plans: list[SourcePlan],
    tenant_targets: dict[str, str],
    client,
    control_target: str | None = None,
) -> None:
    control_target = control_target or plans[0].target_name
    for plan in plans:
        store = DocStore(
            client[control_target],
            client=client,
            collection_prefix=None if not plan.tenant_id else plan.target_name,
        )
        ensure_indexes(store)
        tables = _tables_in_plan(plan)
        for collection, table in tables.items():
            target = store._collection(collection)
            batch: list[dict[str, Any]] = []
            with plan.engine.connect().execution_options(stream_results=True) as connection:
                for row in connection.execute(select(table)).mappings():
                    document = _document_for_target(
                        store, collection, dict(row), tenant_targets, plan
                    )
                    if target.find_one({"_id": document["_id"]}) is None:
                        batch.append(document)
                    if len(batch) >= 500:
                        target.insert_many(batch, ordered=True)
                        batch.clear()
                if batch:
                    target.insert_many(batch, ordered=True)

            with plan.engine.connect() as connection:
                source_count = int(
                    connection.execute(select(func.count()).select_from(table)).scalar_one()
                )
            target_count = target.count_documents({})
            if target_count < source_count:
                raise RuntimeError(
                    f"Verification failed for {plan.label}.{collection}: "
                    "MongoDB contains fewer rows than the source"
                )
            print(f"{plan.label}.{collection}: {source_count} source rows; verified")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write missing documents to Atlas; without this flag, only inspect source row counts",
    )
    args = parser.parse_args()

    source_url = settings.LEGACY_DATABASE_URL.strip()
    if not source_url:
        parser.error("Set LEGACY_DATABASE_URL locally to the rotated legacy PostgreSQL/SQLite URL")
    if args.apply and (
        not settings.MONGODB_URI
        or not settings.MONGODB_URI.startswith(("mongodb://", "mongodb+srv://"))
    ):
        parser.error("Set MONGODB_URI locally to the MongoDB Atlas connection string")

    prefix = settings.MONGODB_DB_PREFIX
    if not prefix or len(prefix) > 30:
        parser.error("MONGODB_DB_PREFIX must contain 1-30 characters")
    control_target = prefix

    plans: list[SourcePlan] = []
    try:
        plans, tenant_targets = _build_plans(source_url, control_target)
        for plan in plans:
            for collection, table in _tables_in_plan(plan).items():
                with plan.engine.connect() as connection:
                    count = connection.execute(
                        select(func.count()).select_from(table)
                    ).scalar_one()
                print(f"{plan.label}.{collection}: {count} source rows")

        if not args.apply:
            print("Dry run only; no MongoDB connection or writes were made.")
            return 0

        client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation="standard",
            tz_aware=True,
        )
        try:
            client.admin.command("ping")
            _preflight(plans, tenant_targets, control_target, client)
            _copy(plans, tenant_targets, client, control_target)
        finally:
            client.close()
    except Exception as exc:
        # Database driver exceptions can embed connection details; do not print them.
        print(f"Migration stopped ({type(exc).__name__}); no credentials were printed.")
        return 1
    finally:
        for plan in plans:
            plan.engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
