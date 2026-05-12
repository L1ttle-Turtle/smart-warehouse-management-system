"""module 7 delivery proof

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-13 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("shipments", sa.Column("delivery_recipient_name", sa.String(length=120), nullable=True))
    op.add_column("shipments", sa.Column("delivery_proof_note", sa.String(length=255), nullable=True))
    op.add_column("shipments", sa.Column("delivery_proof_image_url", sa.String(length=500), nullable=True))
    op.add_column("shipments", sa.Column("delivery_latitude", sa.Float(), nullable=True))
    op.add_column("shipments", sa.Column("delivery_longitude", sa.Float(), nullable=True))
    op.add_column("shipments", sa.Column("delivery_proof_recorded_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("shipments", "delivery_proof_recorded_at")
    op.drop_column("shipments", "delivery_longitude")
    op.drop_column("shipments", "delivery_latitude")
    op.drop_column("shipments", "delivery_proof_image_url")
    op.drop_column("shipments", "delivery_proof_note")
    op.drop_column("shipments", "delivery_recipient_name")
