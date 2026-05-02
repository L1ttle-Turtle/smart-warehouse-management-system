"""module 8 payments minimal

Revision ID: d7e8f9a0b1c2
Revises: c4e5f6a7b8c9
Create Date: 2026-04-28 23:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d7e8f9a0b1c2"
down_revision = "c4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_code", sa.String(length=30), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("bank_account_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_code"),
    )


def downgrade():
    op.drop_table("payments")
