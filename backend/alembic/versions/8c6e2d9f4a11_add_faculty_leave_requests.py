"""add faculty leave requests

Revision ID: 8c6e2d9f4a11
Revises: d75bdbd30bdb
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8c6e2d9f4a11"
down_revision: Union[str, Sequence[str], None] = "d75bdbd30bdb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("faculty_leave_requests"):
        return
    op.create_table(
        "faculty_leave_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("institution_id", sa.String(length=36), nullable=False),
        sa.Column("faculty_id", sa.String(length=36), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reviewed_by_id", sa.String(length=36), nullable=True),
        sa.Column("review_comments", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faculty_leave_requests_id", "faculty_leave_requests", ["id"])
    op.create_index("ix_faculty_leave_requests_institution_id", "faculty_leave_requests", ["institution_id"])
    op.create_index("ix_faculty_leave_requests_faculty_id", "faculty_leave_requests", ["faculty_id"])
    op.create_index("ix_faculty_leave_requests_status", "faculty_leave_requests", ["status"])


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("faculty_leave_requests"):
        return
    op.drop_index("ix_faculty_leave_requests_status", table_name="faculty_leave_requests")
    op.drop_index("ix_faculty_leave_requests_faculty_id", table_name="faculty_leave_requests")
    op.drop_index("ix_faculty_leave_requests_institution_id", table_name="faculty_leave_requests")
    op.drop_index("ix_faculty_leave_requests_id", table_name="faculty_leave_requests")
    op.drop_table("faculty_leave_requests")
