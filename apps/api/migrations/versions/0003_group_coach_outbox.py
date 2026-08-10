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
    columns = {column["name"]: column for column in inspector.get_columns("outbox_events")}
    if not columns["fitcrew_user_id"]["nullable"]:
        op.alter_column(
            "outbox_events", "fitcrew_user_id", existing_type=sa.String(36), nullable=True
        )
    additions = {
        "idempotency_key": sa.Column("idempotency_key", sa.String(160)),
        "scheduled_for": sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        "next_attempt_at": sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        "last_error_code": sa.Column("last_error_code", sa.String(64)),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("outbox_events", column)
    unique_column_sets = {
        tuple(constraint.get("column_names") or ())
        for constraint in inspector.get_unique_constraints("outbox_events")
    }
    if ("idempotency_key",) not in unique_column_sets:
        op.create_unique_constraint(
            "uq_outbox_events_idempotency_key", "outbox_events", ["idempotency_key"]
        )
    indexes = {index["name"] for index in inspector.get_indexes("outbox_events")}
    if "ix_outbox_events_scheduled_for" not in indexes:
        op.create_index("ix_outbox_events_scheduled_for", "outbox_events", ["scheduled_for"])
    if "ix_outbox_events_next_attempt_at" not in indexes:
        op.create_index("ix_outbox_events_next_attempt_at", "outbox_events", ["next_attempt_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"]: column for column in inspector.get_columns("outbox_events")}
    indexes = {index["name"] for index in inspector.get_indexes("outbox_events")}
    if "ix_outbox_events_next_attempt_at" in indexes:
        op.drop_index("ix_outbox_events_next_attempt_at", table_name="outbox_events")
    if "ix_outbox_events_scheduled_for" in indexes:
        op.drop_index("ix_outbox_events_scheduled_for", table_name="outbox_events")
    for constraint in inspector.get_unique_constraints("outbox_events"):
        if tuple(constraint.get("column_names") or ()) == ("idempotency_key",):
            op.drop_constraint(constraint["name"], "outbox_events", type_="unique")
    for name in ("last_error_code", "next_attempt_at", "scheduled_for", "idempotency_key"):
        if name in columns:
            op.drop_column("outbox_events", name)
    op.execute(sa.text("DELETE FROM outbox_events WHERE fitcrew_user_id IS NULL"))
    if columns["fitcrew_user_id"]["nullable"]:
        op.alter_column(
            "outbox_events", "fitcrew_user_id", existing_type=sa.String(36), nullable=False
        )
