"""auth token blocklist

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e6f7
Create Date: 2026-05-12 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e6f7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "token_blocklist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(op.f("ix_token_blocklist_expires_at"), "token_blocklist", ["expires_at"], unique=False)
    op.create_index(op.f("ix_token_blocklist_jti"), "token_blocklist", ["jti"], unique=False)
    op.create_index(op.f("ix_token_blocklist_revoked_at"), "token_blocklist", ["revoked_at"], unique=False)
    op.create_index(op.f("ix_token_blocklist_user_id"), "token_blocklist", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_token_blocklist_user_id"), table_name="token_blocklist")
    op.drop_index(op.f("ix_token_blocklist_revoked_at"), table_name="token_blocklist")
    op.drop_index(op.f("ix_token_blocklist_jti"), table_name="token_blocklist")
    op.drop_index(op.f("ix_token_blocklist_expires_at"), table_name="token_blocklist")
    op.drop_table("token_blocklist")
