from pathlib import Path
from typing import Generator, Optional

from fastapi import Request
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Determine engine parameters based on database driver
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
_tenant_session_factories = {}

Base = declarative_base()


def ensure_control_schema() -> None:
    """Apply additive control-plane changes without disrupting existing local databases."""
    columns = {column["name"] for column in inspect(engine).get_columns("institutions")}
    settings_columns = {column["name"] for column in inspect(engine).get_columns("institution_settings")}
    if "database_url" not in columns or "institution_type" not in columns or len(settings_columns) < 9:
        with engine.begin() as connection:
            if "database_url" not in columns:
                connection.execute(text("ALTER TABLE institutions ADD COLUMN database_url TEXT"))
            if "institution_type" not in columns:
                connection.execute(text("ALTER TABLE institutions ADD COLUMN institution_type VARCHAR(40) NOT NULL DEFAULT 'OTHER'"))
            additions = [
                ("institution_type", "VARCHAR(40) NOT NULL DEFAULT 'OTHER'"),
                ("academic_unit_label", "VARCHAR(80) NOT NULL DEFAULT 'Department / Class'"),
                ("educator_label", "VARCHAR(80) NOT NULL DEFAULT 'Faculty / Teacher'"),
                ("learner_label", "VARCHAR(80) NOT NULL DEFAULT 'Student'"),
                ("head_role_label", "VARCHAR(80) NOT NULL DEFAULT 'Head / Principal'"),
            ]
            for column_name, definition in additions:
                if column_name not in settings_columns:
                    connection.execute(text(f"ALTER TABLE institution_settings ADD COLUMN {column_name} {definition}"))


def ensure_tenant_schema(tenant_engine) -> None:
    """Add new configurable terminology fields to existing tenant databases."""
    columns = {column["name"] for column in inspect(tenant_engine).get_columns("institutions")}
    settings_columns = {column["name"] for column in inspect(tenant_engine).get_columns("institution_settings")}
    additions = [
        ("institutions", columns, "institution_type VARCHAR(40) NOT NULL DEFAULT 'OTHER'"),
        ("institution_settings", settings_columns, "institution_type VARCHAR(40) NOT NULL DEFAULT 'OTHER'"),
        ("institution_settings", settings_columns, "academic_unit_label VARCHAR(80) NOT NULL DEFAULT 'Department / Class'"),
        ("institution_settings", settings_columns, "educator_label VARCHAR(80) NOT NULL DEFAULT 'Faculty / Teacher'"),
        ("institution_settings", settings_columns, "learner_label VARCHAR(80) NOT NULL DEFAULT 'Student'"),
        ("institution_settings", settings_columns, "head_role_label VARCHAR(80) NOT NULL DEFAULT 'Head / Principal'"),
    ]
    with tenant_engine.begin() as connection:
        for table, existing, definition in additions:
            column_name = definition.split(" ", 1)[0]
            if column_name not in existing:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))


def _tenant_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        database_path = Path(database_url.removeprefix("sqlite:///"))
        if not database_path.is_absolute():
            database_path = Path(__file__).resolve().parents[2] / database_path
        return f"sqlite:///{database_path}"
    return database_url


def get_tenant_session_factory(database_url: str):
    """Return a cached SQLAlchemy session factory for a provisioned institute database."""
    normalized_url = _tenant_database_url(database_url)
    if normalized_url not in _tenant_session_factories:
        tenant_engine = create_engine(
            normalized_url,
            connect_args={"check_same_thread": False} if normalized_url.startswith("sqlite") else {},
            pool_pre_ping=True,
            echo=False,
        )
        _tenant_session_factories[normalized_url] = sessionmaker(
            autocommit=False, autoflush=False, bind=tenant_engine
        )
        ensure_tenant_schema(tenant_engine)
    return _tenant_session_factories[normalized_url]


def get_db(request: Request = None) -> Generator:
    """Yield the control or selected institute session for the current request."""
    session_factory = SessionLocal
    institution_id = request.headers.get("X-Institution-ID") if request else None
    if institution_id:
        control_db = SessionLocal()
        try:
            from app.models.institution import Institution
            institution = control_db.query(Institution).filter(Institution.id == institution_id).first()
            if institution and institution.database_url:
                session_factory = get_tenant_session_factory(institution.database_url)
        finally:
            control_db.close()

    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def provision_tenant_database(institution, principal_email: Optional[str] = None,
                              principal_password: Optional[str] = None,
                              principal_first_name: str = "Institution",
                              principal_last_name: str = "Principal") -> str:
    """Create an isolated database and bootstrap its institute-level records."""
    from app.core.security import get_password_hash
    from app.models.institution import Institution, InstitutionSetting
    from app.models.user import Role, User, UserRoleAssignment
    import app.models  # noqa: F401 - register every model before create_all

    data_dir = Path(__file__).resolve().parents[2] / "tenant_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    database_path = data_dir / f"{institution.slug}.db"
    database_url = f"sqlite:///{database_path}"
    tenant_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
        echo=False,
    )
    Base.metadata.create_all(bind=tenant_engine)
    tenant_session = sessionmaker(autocommit=False, autoflush=False, bind=tenant_engine)
    db = tenant_session()
    try:
        tenant_institution = Institution(
            id=institution.id,
            slug=institution.slug,
            name=institution.name,
            code=institution.code,
            status=institution.status,
            address=institution.address,
            city=institution.city,
            state=institution.state,
            pincode=institution.pincode,
            phone=institution.phone,
            email=institution.email,
            logo_url=institution.logo_url,
            institution_type=institution.institution_type,
        )
        db.add(tenant_institution)
        db.add(InstitutionSetting(institution_id=institution.id, institution_type=institution.institution_type))
        role_names = ["SUPER_ADMIN", "PRINCIPAL", "FACULTY", "STUDENT", "PARENT", "OFFICE_STAFF"]
        roles = {}
        for role_name in role_names:
            role = Role(name=role_name, description=f"{role_name} role permissions")
            db.add(role)
            db.flush()
            roles[role_name] = role
        if principal_email and principal_password:
            username = principal_email.split("@", 1)[0]
            principal = User(
                institution_id=institution.id,
                username=username,
                email=principal_email,
                password_hash=get_password_hash(principal_password),
                first_name=principal_first_name,
                last_name=principal_last_name,
                is_active=True,
                is_verified=True,
            )
            db.add(principal)
            db.flush()
            db.add(UserRoleAssignment(
                user_id=principal.id,
                role_id=roles["PRINCIPAL"].id,
                institution_id=institution.id,
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    _tenant_session_factories.pop(database_url, None)
    return database_url
