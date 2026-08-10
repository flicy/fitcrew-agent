"""Add idempotent proactive group-coach Outbox fields.

Revision ID: 0003_group_coach_outbox
Revises: 0002_pairing_exchange_sessions
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_group_coach_outbox"
down_revision = "0002_pairing_exchange_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("outbox_events")}
    if "idempotency_key" in columns:
        return
    op.alter_column("outbox_events", "fitcrew_user_id", existing_type=sa.String(36), nullable=True)
    op.add_column("outbox_events", sa.Column("idempotency_key", sa.String(160)))
    op.add_column("outbox_events", sa.Column("scheduled_for", sa.DateTime(timezone=True)))
    op.add_column("outbox_events", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("outbox_events", sa.Column("last_error_code", sa.String(64)))
    op.create_unique_constraint(
        "uq_outbox_events_idempotency_key", "outbox_events", ["idempotency_key"]
    )
    op.create_index("ix_outbox_events_scheduled_for", "outbox_events", ["scheduled_for"])
    op.create_index("ix_outbox_events_next_attempt_at", "outbox_events", ["next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_events_next_attempt_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_scheduled_for", table_name="outbox_events")
    op.drop_constraint("uq_outbox_events_idempotency_key", "outbox_events", type_="unique")
    op.drop_column("outbox_events", "last_error_code")
    op.drop_column("outbox_events", "next_attempt_at")
    op.drop_column("outbox_events", "scheduled_for")
    op.drop_column("outbox_events", "idempotency_key")
    op.alter_column("outbox_events", "fitcrew_user_id", existing_type=sa.String(36), nullable=False)
