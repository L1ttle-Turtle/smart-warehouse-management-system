"""module 6.5 stocktakes

Revision ID: f1b2c3d4e5f6
Revises: c8b9f2a4d301
Create Date: 2026-04-25 11:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1b2c3d4e5f6"
down_revision = "c8b9f2a4d301"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stocktakes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stocktake_code", sa.String(length=30), nullable=False),
        sa.Column("warehouse_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("cancelled_by", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stocktake_code"),
    )
    op.create_table(
        "stocktake_details",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stocktake_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("system_quantity", sa.Float(), nullable=False),
        sa.Column("actual_quantity", sa.Float(), nullable=False),
        sa.Column("difference_quantity", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["stocktake_id"], ["stocktakes.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["warehouse_locations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stocktake_id",
            "product_id",
            "location_id",
            name="uq_stocktake_detail_product_location",
        ),
    )


def downgrade():
    op.drop_table("stocktake_details")
    op.drop_table("stocktakes")
