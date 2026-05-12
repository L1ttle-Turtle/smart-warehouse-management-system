"""stocktake multi-level approval

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-13 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("stocktakes", sa.Column("submitted_by", sa.Integer(), nullable=True))
    op.add_column("stocktakes", sa.Column("rejected_by", sa.Integer(), nullable=True))
    op.add_column(
        "stocktakes",
        sa.Column(
            "current_approval_level",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "stocktakes",
        sa.Column(
            "required_approval_levels",
            sa.Integer(),
            server_default="2",
            nullable=False,
        ),
    )
    op.add_column("stocktakes", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    op.add_column("stocktakes", sa.Column("rejected_at", sa.DateTime(), nullable=True))
    op.create_table(
        "stocktake_approvals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stocktake_id", sa.Integer(), nullable=False),
        sa.Column("approval_level", sa.Integer(), nullable=False),
        sa.Column("approver_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["stocktake_id"], ["stocktakes.id"]),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stocktake_id",
            "approval_level",
            name="uq_stocktake_approval_level",
        ),
    )


def downgrade():
    op.drop_table("stocktake_approvals")
    op.drop_column("stocktakes", "rejected_at")
    op.drop_column("stocktakes", "submitted_at")
    op.drop_column("stocktakes", "required_approval_levels")
    op.drop_column("stocktakes", "current_approval_level")
    op.drop_column("stocktakes", "rejected_by")
    op.drop_column("stocktakes", "submitted_by")
