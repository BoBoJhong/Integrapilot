"""init metadata tables

Revision ID: 20260327_01
Revises:
Create Date: 2026-03-27 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260327_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("backstory", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "input_assets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("slot", sa.String(length=1), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("upload_id", sa.String(length=64), nullable=True),
        sa.Column("origin_url", sa.Text(), nullable=True),
        sa.Column("branch", sa.String(length=120), nullable=True),
        sa.Column("resolved_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("report_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("project_a_path", sa.Text(), nullable=False),
        sa.Column("project_b_path", sa.Text(), nullable=False),
        sa.Column("input_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_report_name", "reports", ["report_name"], unique=False)

    op.create_table(
        "assessment_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("project_a_path", sa.Text(), nullable=False),
        sa.Column("project_b_path", sa.Text(), nullable=False),
        sa.Column("input_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("report_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("assessment_jobs")
    op.drop_index("ix_reports_report_name", table_name="reports")
    op.drop_table("reports")
    op.drop_table("input_assets")
    op.drop_table("agents")
