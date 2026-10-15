"""Add role-specific applications and preparation plans; preserve tracked companies."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def timestamps():
    return [sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())]


def upgrade():
    op.create_table('applications',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('company_name', sa.String(160), nullable=False),
        sa.Column('role', sa.String(160), nullable=False),
        sa.Column('stage', sa.String(32), nullable=False, server_default='Saved'),
        sa.Column('deadline', sa.Date()),
        sa.Column('next_action', sa.String(300), nullable=False, server_default=''),
        sa.Column('notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('resume_id', UUID(), sa.ForeignKey('resumes.id', ondelete='SET NULL')),
        sa.Column('history', sa.JSON(), nullable=False, server_default='[]'),
        *timestamps(),
    )
    op.create_index('ix_applications_user_id', 'applications', ['user_id'])
    op.create_table('preparation_tasks',
        sa.Column('id', UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('details', sa.Text(), nullable=False, server_default=''),
        sa.Column('due_date', sa.Date()),
        sa.Column('minutes', sa.Integer(), nullable=False, server_default='25'),
        sa.Column('is_done', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('source_analysis_id', UUID(), sa.ForeignKey('resume_job_match_analyses.id', ondelete='SET NULL')),
        sa.Column('source_index', sa.Integer()),
        sa.Column('source_label', sa.String(330)),
        *timestamps(),
    )
    op.create_index('ix_preparation_tasks_user_id', 'preparation_tasks', ['user_id'])
    op.create_index('uq_task_analysis_requirement', 'preparation_tasks', ['user_id', 'source_analysis_id', 'source_index'], unique=True)
    # Carry existing tracking into the pipeline once. Company preparation data
    # remains untouched. The imported role explicitly asks the user to name it.
    op.execute("""INSERT INTO applications (user_id, company_name, role, stage, deadline, notes, history)
        SELECT uc.user_id, c.name, 'Role to be added',
        CASE uc.application_status WHEN 'Applied' THEN 'Applied' WHEN 'OA Received' THEN 'Assessment'
          WHEN 'Interview Scheduled' THEN 'Interview' WHEN 'Offer Received' THEN 'Offer'
          WHEN 'Rejected' THEN 'Closed' ELSE 'Saved' END,
        uc.deadline::date, COALESCE(uc.notes_summary, ''), '[]'::json
        FROM user_company uc JOIN companies c ON c.id = uc.company_id""")
    for table in ('applications', 'preparation_tasks'):
        op.execute(f'CREATE TRIGGER set_updated_at BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION set_updated_at()')


def downgrade():
    op.drop_table('preparation_tasks')
    op.drop_table('applications')
