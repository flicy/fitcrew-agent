"""Add short-lived invited-user pairing exchanges.

Revision ID: 0002_pairing_exchange_sessions
Revises: 0001_owner_alpha
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_pairing_exchange_sessions"
down_revision = "0001_owner_alpha"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("pairing_exchange_sessions"):
        # The initial alpha migration uses Base.metadata.create_all(), so a fresh
        # install running the newer application model has already created this table.
        return
    op.create_table(
        "pairing_exchange_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fitcrew_user_id", sa.String(length=36), nullable=False),
        sa.Column("device_public_id", sa.String(length=128), nullable=False),
        sa.Column("categories_json", sa.Text(), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("pairing_code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["fitcrew_user_id"], ["users.fitcrew_user_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key_hash"),
        sa.UniqueConstraint("pairing_code_hash"),
    )
    op.create_index(
        "ix_pairing_exchange_sessions_fitcrew_user_id",
        "pairing_exchange_sessions",
        ["fitcrew_user_id"],
    )
    op.create_index(
        "ix_pairing_exchange_sessions_expires_at",
        "pairing_exchange_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pairing_exchange_sessions_expires_at", table_name="pairing_exchange_sessions")
    op.drop_index("ix_pairing_exchange_sessions_fitcrew_user_id", table_name="pairing_exchange_sessions")
    op.drop_table("pairing_exchange_sessions")
