"""module 4 product foundation

Revision ID: a4d92b7c1e11
Revises: f42a6d3c9b10
Create Date: 2026-04-22 10:40:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a4d92b7c1e11"
down_revision = "f42a6d3c9b10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("description", sa.String(length=255), nullable=True))
        batch_op.create_foreign_key(
            "fk_products_category_id_categories",
            "categories",
            ["category_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_constraint("fk_products_category_id_categories", type_="foreignkey")
        batch_op.drop_column("description")
        batch_op.drop_column("category_id")
