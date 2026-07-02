"""add question_logs and question_feedbacks tables

Revision ID: 272dc0d0821a
Revises: f3a1b2c9d4e5
Create Date: 2026-07-02 21:06:13.072542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '272dc0d0821a'
down_revision: Union[str, Sequence[str], None] = 'f3a1b2c9d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('question_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('question', sa.Text(), nullable=False),
    sa.Column('answer', sa.Text(), nullable=False),
    sa.Column('retrieved_fatwa_ids', postgresql.ARRAY(sa.UUID()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_logs_user_id'), 'question_logs', ['user_id'], unique=False)
    op.create_table('question_feedbacks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('question_log_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('feedback', sa.Enum('like', 'dislike', name='feedback_type'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['question_log_id'], ['question_logs.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_question_feedbacks_question_log_id'), 'question_feedbacks', ['question_log_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_question_feedbacks_question_log_id'), table_name='question_feedbacks')
    op.drop_table('question_feedbacks')
    op.drop_index(op.f('ix_question_logs_user_id'), table_name='question_logs')
    op.drop_table('question_logs')