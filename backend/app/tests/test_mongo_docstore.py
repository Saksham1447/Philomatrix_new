from datetime import date, datetime, timezone
from decimal import Decimal

import mongomock
import pytest
from sqlalchemy import Boolean, Column, DateTime, MetaData, String, Table, create_engine

from app.core.database import clear_store_caches, ensure_indexes, get_control_store
from app.core.database import Base
from app.core.docstore import Conflict, DocStore
from app.core.mongo import set_mongo_client
from app.core.schema import COLLECTIONS
from app.core.q import regex_contains


@pytest.fixture
def store():
    client = mongomock.MongoClient(tz_aware=True)
    set_mongo_client(client)
    clear_store_caches()
    try:
        yield get_control_store()
    finally:
        clear_store_caches()
        set_mongo_client(None)


def test_schema_mirrors_every_legacy_table():
    import app.models

    assert len(COLLECTIONS) == 40
    assert set(COLLECTIONS) == set(Base.metadata.tables)
    assert set(COLLECTIONS) == {
        "institutions", "institution_settings", "roles", "users",
        "user_role_assignments", "refresh_token_records", "user_preferences",
        "academic_years", "classes", "divisions", "subjects",
        "faculty_profiles", "faculty_subject_assignments", "students",
        "guardians", "student_guardian_links", "enrollments",
        "timetable_versions", "timetable_entries", "timetable_slots", "attendance_sessions",
        "attendance_records", "attendance_correction_requests",
        "examinations", "exam_subjects", "marks_entries", "marks_approvals",
        "result_publications", "report_card_versions", "assignments",
        "assignment_submissions", "notices", "feedback_forms",
        "feedback_questions", "feedback_responses", "notifications",
        "audit_logs", "study_materials", "faculty_leave_requests",
        "faculty_registration_requests",
    }


def test_unique_indexes_and_foreign_keys_match_legacy_schema():
    import app.models

    def normalize_action(action):
        return (action or "CASCADE").replace("_", " ").upper()

    for name, table in Base.metadata.tables.items():
        sql_unique = {
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        }
        sql_unique |= {
            tuple(index.columns.keys())
            for index in table.indexes
            if index.unique
        }
        mongo_unique = {
            index.fields for index in COLLECTIONS[name].indexes if index.unique
        }
        assert mongo_unique == sql_unique, name

        sql_foreign_keys = {
            (
                key.parent.name,
                key.column.table.name,
                normalize_action(key.ondelete),
            )
            for key in table.foreign_keys
        }
        mongo_foreign_keys = {
            (key.field, key.collection, normalize_action(key.on_delete))
            for key in COLLECTIONS[name].fks
        }
        assert mongo_foreign_keys == sql_foreign_keys, name


def test_like_search_wildcards_keep_sql_semantics():
    import re

    contains_many = regex_contains("a%b")["$regex"]
    contains_one = regex_contains("a_b")["$regex"]
    assert re.search(contains_many, "axxxb", re.IGNORECASE)
    assert re.search(contains_one, "a-b", re.IGNORECASE)
    assert not re.search(contains_one, "axxb", re.IGNORECASE)


def test_crud_preserves_string_ids_and_user_properties(store):
    user = store.insert("users", {
        "id": "legacy-user-1",
        "username": "ada",
        "email": "ada@example.test",
        "password_hash": "hash",
        "first_name": "Ada",
        "last_name": "Lovelace",
    })

    assert user.id == "legacy-user-1"
    assert store.get("users", user.id).full_name == "Ada Lovelace"
    assert store.find_one("users", {"email": "ada@example.test"}).id == user.id

    store.update(user, {"first_name": "Augusta"})
    assert store.get("users", user.id).first_name == "Augusta"


def test_unique_constraints_raise_domain_conflict(store):
    values = {
        "username": "same",
        "email": "same@example.test",
        "password_hash": "hash",
        "first_name": "First",
        "last_name": "User",
    }
    store.insert("users", values)
    with pytest.raises(Conflict):
        store.insert("users", {**values, "id": "another-user"})


def test_nullable_compound_unique_constraint_matches_sql_null_semantics(store):
    user = store.insert("users", {
        "username": "global-assignment-user",
        "email": "global-assignment@example.test",
        "password_hash": "hash",
        "first_name": "Global",
        "last_name": "User",
    })
    role = store.insert("roles", {"name": "GLOBAL_ASSIGNMENT", "description": "Test role"})
    institution = store.insert("institutions", {
        "id": "institution-a",
        "slug": "institution-a",
        "name": "Institution A",
        "code": "IA-1",
    })
    assignment = {"user_id": user.id, "role_id": role.id}
    store.insert("user_role_assignments", {**assignment, "institution_id": None})
    store.insert("user_role_assignments", {**assignment, "institution_id": None})
    store.insert("user_role_assignments", {**assignment, "institution_id": institution.id})
    with pytest.raises(Conflict):
        store.insert("user_role_assignments", {**assignment, "institution_id": institution.id})


def test_typed_values_and_collection_relationships_round_trip(store):
    institution = store.insert("institutions", {
        "id": "inst-1",
        "slug": "demo",
        "name": "Demo",
        "code": "D-1",
    })
    year = store.insert("academic_years", {
        "id": "year-1",
        "institution_id": institution.id,
        "name": "2026-27",
        "start_date": date(2026, 4, 1),
        "end_date": date(2027, 3, 31),
        "is_current": True,
    })
    setting = store.insert("institution_settings", {
        "institution_id": institution.id,
        "min_attendance_threshold": Decimal("75.50"),
    })

    assert store.get("academic_years", year.id).start_date == date(2026, 4, 1)
    assert store.get("academic_years", year.id).created_at.tzinfo == timezone.utc
    assert store.get("institution_settings", setting.id).min_attendance_threshold == Decimal("75.50")


def test_json_documents_preserve_decimal_precision_and_mongo_special_keys(store):
    state = {"$state": "published", "nested.value": Decimal("0.1234567890123456789")}
    log = store.insert("audit_logs", {
        "action": "TEST",
        "entity_type": "result",
        "entity_id": "result-1",
        "new_state": state,
    })

    assert store.get("audit_logs", log.id).new_state == state


def test_delete_applies_declared_cascade_rules(store):
    institution = store.insert("institutions", {
        "id": "inst-delete",
        "slug": "delete",
        "name": "Delete",
        "code": "D-2",
    })
    store.insert("institution_settings", {"institution_id": institution.id})

    assert store.delete("institutions", institution.id)
    assert store.count("institution_settings", {"institution_id": institution.id}) == 0


def test_update_does_not_change_creation_timestamp(store):
    user = store.insert("users", {
        "username": "timestamp",
        "email": "timestamp@example.test",
        "password_hash": "hash",
        "first_name": "Time",
        "last_name": "Stamp",
    })
    created_at = user.created_at
    store.update(user, {"phone_number": "123"})

    updated = store.get("users", user.id)
    assert updated.created_at == created_at
    assert isinstance(updated.updated_at, datetime)


def test_legacy_row_migration_preserves_id_and_values(tmp_path):
    import migrate_to_mongodb

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    metadata = MetaData()
    users = Table(
        "users",
        metadata,
        Column("id", String, primary_key=True),
        Column("username", String, nullable=False),
        Column("email", String, nullable=False),
        Column("password_hash", String, nullable=False),
        Column("first_name", String, nullable=False),
        Column("last_name", String, nullable=False),
        Column("is_active", Boolean, nullable=False),
        Column("is_verified", Boolean, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)
    created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(users.insert(), {
            "id": "legacy-user-7",
            "username": "migrated",
            "email": "migrated@example.test",
            "password_hash": "legacy-hash",
            "first_name": "Migrated",
            "last_name": "User",
            "is_active": True,
            "is_verified": True,
            "created_at": created_at,
            "updated_at": created_at,
        })

    client = mongomock.MongoClient(tz_aware=True)
    target = DocStore(client["migration_test"], client=client)
    ensure_indexes(target)
    plan = migrate_to_mongodb.SourcePlan("control", engine, "migration_test")
    migrate_to_mongodb._preflight([plan], {}, "migration_test", client)
    migrate_to_mongodb._copy([plan], {}, client)

    migrated = target.get("users", "legacy-user-7")
    assert migrated is not None
    assert migrated.email == "migrated@example.test"
    assert migrated.password_hash == "legacy-hash"
    assert migrated.created_at == created_at

    engine.dispose()
    client.close()


def test_missing_legacy_sqlite_file_is_not_created(tmp_path):
    import migrate_to_mongodb

    source = tmp_path / "not-present.db"
    with pytest.raises(FileNotFoundError):
        migrate_to_mongodb._new_engine(f"sqlite:///{source}")
    assert not source.exists()


def test_institute_database_is_named_after_the_college():
    from app.core.database import _safe_tenant_db_name

    name = _safe_tenant_db_name({
        "id": "inst-1",
        "name": "Chate Junior College of Science, Kolhapur",
        "slug": "chate-jc",
    })
    assert name == "Chate_Junior_College_Science_Kolhapur"
    assert len(name) <= 38

    long_name = _safe_tenant_db_name({"id": "inst-2", "name": "A" * 60})
    assert len(long_name) <= 38 and long_name.startswith("AAAA")
    assert _safe_tenant_db_name({"id": "inst-3", "name": "Admin"}) != "Admin"


def test_provisioned_institutes_get_college_prefixed_collections_in_configured_database(store, monkeypatch):
    from app.core.config import settings
    from app.core.database import provision_tenant_database, get_tenant_store

    monkeypatch.setattr(settings, "MONGODB_TENANT_COLLECTIONS_DB", "Philomatrix_ERP")
    first = store.insert("institutions", {
        "slug": "chate", "name": "Chate Junior College of Science, Kolhapur", "code": "CH-1",
    })
    second = store.insert("institutions", {
        "slug": "chate-2", "name": "Chate Junior College of Science Kolhapur", "code": "CH-2",
    })
    first_db = provision_tenant_database(first, "p1@example.test", "Password@123")
    second_db = provision_tenant_database(second)

    assert first_db == "Chate_Junior_College_Science_Kolhapur"
    assert second_db != first_db
    first_store = get_tenant_store(first_db)
    second_store = get_tenant_store(second_db)
    assert first_store.name == second_store.name == "Philomatrix_ERP"
    assert first_store.physical_collection_name("users") == f"{first_db}__users"
    assert second_store.physical_collection_name("users") == f"{second_db}__users"
    assert first_store.count("users") == 1
    assert first_store.count("institutions") == 1
    assert first_store.count("subjects") == 10
    assert second_store.count("users") == 0
    assert store.count("users") == 0
    assert "Philomatrix_ERP" in store._client.list_database_names()


def test_tenant_store_reads_legacy_prefixed_collections_until_migrated(store):
    from app.core.database import get_tenant_store

    legacy = DocStore(store._database, client=store._client, collection_prefix="legacy_college")
    ensure_indexes(legacy)
    legacy.insert("institutions", {
        "id": "legacy-institution",
        "name": "Legacy College",
        "slug": "legacy-college",
        "code": "LEGACY-1",
    })

    tenant = get_tenant_store("legacy_college")

    assert tenant.name == "philomatrix"
    assert tenant.physical_collection_name("institutions") == "legacy_college__institutions"
    assert tenant.find_one("institutions", {"code": "LEGACY-1"}).id == "legacy-institution"


def test_tenant_store_prefers_configured_shared_database_namespace(store, monkeypatch):
    from app.core.config import settings
    from app.core.database import get_tenant_store

    monkeypatch.setattr(settings, "MONGODB_TENANT_COLLECTIONS_DB", "Philomatrix_ERP")
    shared = DocStore(
        store._client["Philomatrix_ERP"],
        client=store._client,
        collection_prefix="shared_college",
    )
    ensure_indexes(shared)
    shared.insert("classes", {"id": "shared-class", "name": "Shared class"})
    separate = DocStore(store._client["shared_college"], client=store._client)
    ensure_indexes(separate)
    separate.insert("classes", {"id": "separate-class", "name": "Separate class"})

    tenant = get_tenant_store("shared_college")

    assert tenant.name == "Philomatrix_ERP"
    assert tenant.find_one("classes", {"id": "shared-class"}).name == "Shared class"


def test_tenant_migration_copies_and_verifies_before_switching_registry(store):
    from app.core.database import get_tenant_store
    from migrate_tenant_to_database import migrate_institution

    institution = store.insert("institutions", {
        "slug": "migration-college",
        "name": "Migration College",
        "code": "MIG-1",
        "database_url": "Legacy_Migration_College",
    })
    source = DocStore(
        store._database,
        client=store._client,
        collection_prefix=institution.database_url,
    )
    ensure_indexes(source)
    source.insert("institutions", {
        "id": institution.id,
        "slug": institution.slug,
        "name": institution.name,
        "code": institution.code,
        "database_url": institution.database_url,
    })
    source.insert("classes", {
        "id": "migration-class-1",
        "institution_id": institution.id,
        "name": "Class 11",
    })

    migrate_institution(store, store._client, institution, apply=True)

    tenant = get_tenant_store(institution.database_url)
    assert tenant.name == "Migration_College"
    assert tenant.get("classes", "migration-class-1").name == "Class 11"
    assert tenant.get("institutions", institution.id).database_url == "Migration_College"
    assert source.count("classes") == 1


def test_tenant_database_migration_copies_to_prefixed_shared_collections(store, monkeypatch):
    from app.core.config import settings
    from app.core.database import get_tenant_store
    from migrate_tenant_to_collections import migrate_institution

    monkeypatch.setattr(settings, "MONGODB_TENANT_COLLECTIONS_DB", "Philomatrix_ERP")
    institution = store.insert("institutions", {
        "slug": "shared-migration-college",
        "name": "Shared Migration College",
        "code": "SHARED-1",
        "database_url": "Shared_Migration_College",
    })
    source = DocStore(
        store._client["Shared_Migration_College"],
        client=store._client,
    )
    ensure_indexes(source)
    source.insert("institutions", {
        "id": institution.id,
        "slug": institution.slug,
        "name": institution.name,
        "code": institution.code,
        "database_url": institution.database_url,
    })
    source.insert("classes", {
        "id": "shared-migration-class-1",
        "institution_id": institution.id,
        "name": "Class 11",
    })

    migrate_institution(store, store._client, institution, apply=True)

    tenant = get_tenant_store(institution.database_url)
    assert tenant.name == "Philomatrix_ERP"
    assert tenant.collection_prefix == "Shared_Migration_College"
    assert tenant.get("classes", "shared-migration-class-1").name == "Class 11"
    assert source.count("classes") == 1
