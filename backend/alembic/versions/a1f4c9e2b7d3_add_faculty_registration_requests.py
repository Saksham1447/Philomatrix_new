"""add faculty registration requests

Revision ID: a1f4c9e2b7d3
Revises: 8c6e2d9f4a11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1f4c9e2b7d3"
down_revision: Union[str, Sequence[str], None] = "8c6e2d9f4a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("faculty_registration_requests"):
        return
    op.create_table(
        "faculty_registration_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("institution_id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("phone_number", sa.String(length=30), nullable=True),
        sa.Column("employee_id", sa.String(length=50), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("qualification", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by_id", sa.String(length=36), nullable=True),
        sa.Column("review_comments", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faculty_registration_requests_id", "faculty_registration_requests", ["id"])
    op.create_index("ix_faculty_registration_requests_institution_id", "faculty_registration_requests", ["institution_id"])
    op.create_index("ix_faculty_registration_requests_status", "faculty_registration_requests", ["status"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("faculty_registration_requests"):
        op.drop_index("ix_faculty_registration_requests_status", table_name="faculty_registration_requests")
        op.drop_index("ix_faculty_registration_requests_institution_id", table_name="faculty_registration_requests")
        op.drop_index("ix_faculty_registration_requests_id", table_name="faculty_registration_requests")
        op.drop_table("faculty_registration_requests")
