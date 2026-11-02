"""Crea la tabla itineraries

Revision ID: a3f1e2b4c5d0
Revises:
Create Date: 2026-11-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3f1e2b4c5d0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "itineraries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("traveler_name", sa.String(255), nullable=False),
        sa.Column("traveler_email", sa.String(255), nullable=True),
        sa.Column("departure_airport_id", sa.Integer(), nullable=False),
        sa.Column("arrival_airport_id", sa.Integer(), nullable=False),
        sa.Column("travel_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("itineraries")
