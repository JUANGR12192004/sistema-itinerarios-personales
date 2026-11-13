"""Agrega traceparent a outbox_events para propagar trazas distribuidas (ADR-037, Fase 9B)

El relay lee el traceparent de cada mensaje pendiente y lo restaura como contexto
OTel activo antes de publicar en RabbitMQ, para que el span de publicación sea hijo
del span de la solicitud HTTP original que creó el itinerario.

Revision ID: e6f0a4b8c1d9
Revises: c4d8e2f6a9b1
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f0a4b8c1d9"
down_revision: Union[str, None] = "c4d8e2f6a9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("traceparent", sa.String(55), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("outbox_events", "traceparent")
