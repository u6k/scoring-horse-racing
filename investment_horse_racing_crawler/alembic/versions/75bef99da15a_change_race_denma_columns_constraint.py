"""Change race denma columns constraint

Revision ID: 75bef99da15a
Revises: 8d77c309043e
Create Date: 2020-02-07 10:11:47.461209

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75bef99da15a'
down_revision = '8d77c309043e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("race_denma", "trainer_id", nullable=True)
    op.alter_column("race_denma", "horse_weight", nullable=True)
    op.alter_column("race_denma", "horse_weight_diff", nullable=True)
    op.alter_column("race_denma", "prize_total_money", type_=sa.Float)

    op.alter_column("horse", "breeder", nullable=True)

    op.alter_column("jockey", "name_kana", nullable=True)
    op.alter_column("jockey", "birthday", nullable=True)
    op.alter_column("jockey", "first_licensing_year", nullable=True)


def downgrade():
    pass
