"""Agrega failed_at a outbox_events para los mensajes venenosos (ADR-027)

Un mensaje con fallo permanente (ilegible o de tipo desconocido) recibe failed_at y deja
de estar pendiente. El índice parcial de pendientes se recrea para excluir también esas filas.

Revision ID: c4d8e2f6a9b1
Revises: b7c2d9e1f4a6
Create Date: 2026-11-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d8e2f6a9b1"
down_revision: Union[str, None] = "b7c2d9e1f4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_outbox_events_pending"


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Un índice parcial no se puede modificar: se borra y se crea con la nueva condición
    op.drop_index(INDEX_NAME, table_name="outbox_events")
    op.create_index(
        INDEX_NAME,
        "outbox_events",
        ["occurred_at"],
        postgresql_where=sa.text("published_at IS NULL AND failed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="outbox_events")
    op.create_index(
        INDEX_NAME,
        "outbox_events",
        ["occurred_at"],
        postgresql_where=sa.text("published_at IS NULL"),
    )
    op.drop_column("outbox_events", "failed_at")
