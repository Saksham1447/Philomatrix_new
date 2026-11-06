"""add fee status and division-specific exam assignments

Revision ID: f2c1a8b7d904
Revises: a1f4c9e2b7d3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2c1a8b7d904"
down_revision: Union[str, Sequence[str], None] = "a1f4c9e2b7d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "students" in tables and "fee_status" not in {
        column["name"] for column in inspector.get_columns("students")
    }:
        op.add_column(
            "students",
            sa.Column("fee_status", sa.String(length=20), nullable=False, server_default="PENDING"),
        )

    if "exam_subjects" in tables:
        exam_columns = {column["name"] for column in inspector.get_columns("exam_subjects")}
        if "division_id" not in exam_columns:
            op.add_column("exam_subjects", sa.Column("division_id", sa.String(length=36), nullable=True))
        if "faculty_id" not in exam_columns:
            op.add_column("exam_subjects", sa.Column("faculty_id", sa.String(length=36), nullable=True))
        if "start_time" not in exam_columns:
            op.add_column("exam_subjects", sa.Column("start_time", sa.Time(), nullable=True))
        if "end_time" not in exam_columns:
            op.add_column("exam_subjects", sa.Column("end_time", sa.Time(), nullable=True))

        unique_names = {
            constraint.get("name")
            for constraint in inspector.get_unique_constraints("exam_subjects")
        }
        foreign_keys = {
            fk.get("name")
            for fk in inspector.get_foreign_keys("exam_subjects")
        }
        with op.batch_alter_table("exam_subjects") as batch:
            if "uq_exam_subject_class" in unique_names:
                batch.drop_constraint("uq_exam_subject_class", type_="unique")
            if "uq_exam_subject_division" not in unique_names:
                batch.create_unique_constraint(
                    "uq_exam_subject_division",
                    ["examination_id", "subject_id", "class_id", "division_id"],
                )
            if "fk_exam_subjects_division_id_divisions" not in foreign_keys:
                batch.create_foreign_key(
                    "fk_exam_subjects_division_id_divisions",
                    "divisions",
                    ["division_id"],
                    ["id"],
                    ondelete="CASCADE",
                )
            if "fk_exam_subjects_faculty_id_faculty_profiles" not in foreign_keys:
                batch.create_foreign_key(
                    "fk_exam_subjects_faculty_id_faculty_profiles",
                    "faculty_profiles",
                    ["faculty_id"],
                    ["id"],
                    ondelete="SET NULL",
                )

    if "class_subjects" not in tables and {
        "institutions", "academic_years", "classes", "subjects"
    }.issubset(tables):
        op.create_table(
            "class_subjects",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("institution_id", sa.String(length=36), nullable=False),
            sa.Column("academic_year_id", sa.String(length=36), nullable=False),
            sa.Column("class_id", sa.String(length=36), nullable=False),
            sa.Column("subject_id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["academic_year_id"], ["academic_years.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("academic_year_id", "class_id", "subject_id", name="uq_class_subject_year"),
        )
        op.create_index("ix_class_subjects_institution_id", "class_subjects", ["institution_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "exam_subjects" in tables:
        unique_names = {c.get("name") for c in inspector.get_unique_constraints("exam_subjects")}
        foreign_keys = {fk.get("name") for fk in inspector.get_foreign_keys("exam_subjects")}
        with op.batch_alter_table("exam_subjects") as batch:
            if "uq_exam_subject_division" in unique_names:
                batch.drop_constraint("uq_exam_subject_division", type_="unique")
            if "fk_exam_subjects_division_id_divisions" in foreign_keys:
                batch.drop_constraint("fk_exam_subjects_division_id_divisions", type_="foreignkey")
            if "fk_exam_subjects_faculty_id_faculty_profiles" in foreign_keys:
                batch.drop_constraint("fk_exam_subjects_faculty_id_faculty_profiles", type_="foreignkey")
            if "uq_exam_subject_class" not in unique_names:
                batch.create_unique_constraint(
                    "uq_exam_subject_class",
                    ["examination_id", "subject_id", "class_id"],
                )
            columns = {column["name"] for column in inspector.get_columns("exam_subjects")}
            if "faculty_id" in columns:
                batch.drop_column("faculty_id")
            if "division_id" in columns:
                batch.drop_column("division_id")
            if "start_time" in columns:
                batch.drop_column("start_time")
            if "end_time" in columns:
                batch.drop_column("end_time")
    if "class_subjects" in tables:
        op.drop_index("ix_class_subjects_institution_id", table_name="class_subjects")
        op.drop_table("class_subjects")
    if "students" in tables and "fee_status" in {
        column["name"] for column in inspector.get_columns("students")
    }:
        op.drop_column("students", "fee_status")
