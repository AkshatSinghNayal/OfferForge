# OfferForge workspace upgrade

## User workflows

- **Today** prioritizes an application deadline or pinned opportunity, shows the preparation plan, and keeps detailed charts in Analytics.
- **Applications** supports multiple roles at a company, board/table views, search, stage filters, persistent pins, next actions, notes, deadlines, a linked resume version, and stage history. Drag cards between columns or use the stage selector with touch/keyboard.
- **Resume results** let users review extracted company/role names before saving an application. Missing and partial requirements can become preparation tasks. Adding the same requirement twice returns the existing task, including across browser sessions.
- **Preparation plan** supports manual tasks, estimated minutes, optional due dates, completion, undo, and removal. Tasks from an analysis keep their recommendation and role context.
- **Calendar** shows application deadlines. Company-specific research and checklists remain in Company library.
- **Settings** saves profile names and changes local-account passwords after checking the current password. Password changes invalidate refresh/reset tokens and require signing in again. Existing short-lived access tokens expire normally.

## Deployment

Deploy the backend and frontend together. Migration `0008` creates `applications` and `preparation_tasks` and copies each existing tracked company into one initial application. Because old records have no role field, they are labelled **Role to be added**. Existing company checklists and notes are preserved. The imported pipeline is independent of the old company preparation data after migration.

Both startup entry points now stop when migration fails rather than stamping an unapplied schema as current. If an environment already has incorrect migration history, repair that history explicitly before deployment; do not stamp the new revision to bypass an error.

No new runtime dependencies, AI credentials, or external services are required for these workflows.

## Verification

```sh
cd frontend
npm run build
npm run lint
```

Backend tests use `unittest`. Integration tests run only when explicitly given a disposable PostgreSQL database that has been migrated to head:

```sh
cd backend
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost/TEST_DB alembic upgrade head
WORKSPACE_TEST_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost/TEST_DB \
  python -m unittest discover -s tests -v
```

Integration coverage includes multiple roles, persistent pins and stage history, nullable deadlines, ownership of applications/resumes/tasks/analyses, input validation, idempotent task creation, completion/undo/removal, profile updates, and current-password verification. Startup tests verify that failed migrations are never stamped as successful.

Browser verification uses synthetic data in an isolated PostgreSQL database; screenshots are not real user activity or live AI results.

## Demo workspace

Use **Access with Demo Account** on the login page, or sign in with
`demo@offerforge.dev` / `Demo@123` after initial demo provisioning.
The demo button provisions the account and applies a versioned, additive upgrade
on existing installations. Ordinary users are never seeded. Repeat logins do not
reset edits or duplicate fixtures; a transaction-level PostgreSQL advisory lock
serializes simultaneous demo logins.

The sample includes all application stages, multiple roles at one company,
pins, deadlines, histories, linked resumes, pending/completed/analysis-derived
tasks, mixed practice statuses, notes, resources, checklists, resume keywords and
a saved analysis. The analysis is explicitly fictional and needs no AI key;
requesting a new analysis still uses the configured AI service. Dates are relative
to the first seed and are not shifted on every login. This is a shared, editable
demo account: use fictional information only.
