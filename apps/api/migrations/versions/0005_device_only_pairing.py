"""Distinguish device connection from legacy health-consent replacement."""

import sqlalchemy as sa
from alembic import op

revision = "0005_device_only_pairing"
down_revision = "0004_product_records"
branch_labels = None
depends_on = None


def upgrade():
    columns = sa.inspect(op.get_bind()).get_columns("pairing_exchange_sessions")
    if "preserve_consents" not in {column["name"] for column in columns}:
        op.add_column(
            "pairing_exchange_sessions",
            sa.Column("preserve_consents", sa.Boolean(), server_default=sa.false(), nullable=False),
        )


def downgrade():
    # Old code would interpret pending device-only links as consent replacement.
    op.execute("DELETE FROM pairing_exchange_sessions WHERE preserve_consents = true")
    op.drop_column("pairing_exchange_sessions", "preserve_consents")
