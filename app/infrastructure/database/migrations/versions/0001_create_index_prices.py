"""create index_prices

Revision ID: 0001
Revises:
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "index_prices",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("timestamp", sa.BigInteger, nullable=False),
        sa.UniqueConstraint("ticker", "timestamp", name="uq_index_prices_ticker_timestamp"),
    )


def downgrade() -> None:
    op.drop_table("index_prices")
