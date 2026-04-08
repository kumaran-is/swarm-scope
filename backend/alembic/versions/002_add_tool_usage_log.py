"""Add tool_usage_log to reports

Revision ID: 002
Revises: 001
Create Date: 2026-04-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "tool_usage_log",
            JSONB,
            nullable=True,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("reports", "tool_usage_log")
