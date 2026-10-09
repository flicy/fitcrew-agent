"""Encrypted private product records on the V2 identity foundation."""

import sqlalchemy as sa
from alembic import op

revision = "0004_product_records"
down_revision = "0003_group_coach_outbox"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "data_generation" not in {c["name"] for c in inspector.get_columns("users")}:
        op.add_column(
            "users", sa.Column("data_generation", sa.Integer(), server_default="0", nullable=False)
        )
    if "expires_at" not in {c["name"] for c in inspector.get_columns("device_bindings")}:
        op.add_column("device_bindings", sa.Column("expires_at", sa.DateTime(timezone=True)))
    if not inspector.has_table("login_challenges"):
        op.create_table(
            "login_challenges",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("nonce", sa.String(128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True)),
        )
    if inspector.has_table("product_records"):
        return
    op.create_table(
        "product_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "fitcrew_user_id", sa.String(36), sa.ForeignKey("users.fitcrew_user_id"), nullable=False
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("resource_key", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payload_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("payload_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("fitcrew_user_id", "kind", "resource_key"),
    )
    op.create_index("ix_product_records_fitcrew_user_id", "product_records", ["fitcrew_user_id"])


def downgrade():
    op.drop_index("ix_product_records_fitcrew_user_id", table_name="product_records")
    op.drop_table("product_records")
    op.drop_table("login_challenges")
    op.drop_column("device_bindings", "expires_at")
    op.drop_column("users", "data_generation")
