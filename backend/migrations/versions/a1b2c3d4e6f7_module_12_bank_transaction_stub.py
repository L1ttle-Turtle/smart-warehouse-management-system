"""module 12 bank transaction stub

Revision ID: a1b2c3d4e6f7
Revises: f2a3b4c5d6e7
Create Date: 2026-05-09 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e6f7"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bank_transaction_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("transaction_code", sa.String(length=30), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("bank_account_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("reconciled_by", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("reconciled_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["bank_account_id"], ["bank_accounts.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["reconciled_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_code"),
    )


def downgrade():
    op.drop_table("bank_transaction_logs")
