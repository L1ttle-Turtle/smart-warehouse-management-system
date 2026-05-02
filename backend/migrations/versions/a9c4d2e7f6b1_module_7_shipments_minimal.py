"""module 7 shipments minimal

Revision ID: a9c4d2e7f6b1
Revises: f1b2c3d4e5f6
Create Date: 2026-04-26 11:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a9c4d2e7f6b1"
down_revision = "f1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_code", sa.String(length=30), nullable=False),
        sa.Column("export_receipt_id", sa.Integer(), nullable=False),
        sa.Column("shipper_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("in_transit_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["export_receipt_id"], ["export_receipts.id"]),
        sa.ForeignKeyConstraint(["shipper_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_code"),
        sa.UniqueConstraint("export_receipt_id", name="uq_shipment_export_receipt"),
    )


def downgrade():
    op.drop_table("shipments")
