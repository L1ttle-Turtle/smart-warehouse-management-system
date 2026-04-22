"""module 3 catalogs

Revision ID: b6f8a7c2d991
Revises: c31d7a2f0b1a
Create Date: 2026-04-21 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b6f8a7c2d991"
down_revision = "c31d7a2f0b1a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_name"),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("supplier_code", sa.String(length=30), nullable=False),
        sa.Column("supplier_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_code"),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_code", sa.String(length=30), nullable=False),
        sa.Column("customer_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_code"),
    )
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("account_number", sa.String(length=50), nullable=False),
        sa.Column("account_holder", sa.String(length=120), nullable=False),
        sa.Column("branch", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_number"),
    )


def downgrade():
    op.drop_table("bank_accounts")
    op.drop_table("customers")
    op.drop_table("suppliers")
    op.drop_table("categories")
