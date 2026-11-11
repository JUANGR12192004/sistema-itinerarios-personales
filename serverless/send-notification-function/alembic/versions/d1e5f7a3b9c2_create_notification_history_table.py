"""Crea la tabla notification_history (historial de notificaciones, ADR-029 y ADR-030)

Revision ID: d1e5f7a3b9c2
Revises:
Create Date: 2026-11-10

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1e5f7a3b9c2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(255), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        # Clave de idempotencia: un solo registro por evento
        sa.UniqueConstraint("event_id", name="uq_notification_history_event_id"),
        sa.CheckConstraint("status IN ('SENT', 'SKIPPED')", name="ck_notification_history_status"),
    )


def downgrade() -> None:
    op.drop_table("notification_history")
