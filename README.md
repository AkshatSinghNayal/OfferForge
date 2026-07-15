# OfferForge

A professional placement preparation hub — DSA tracking, company checklists, resume management, calendar milestones, and real-time analytics, unified in a single dashboard.

---

## Screenshots

| Desktop Dashboard |
|:-:|
| ![](frontend/public/screenshots/DesktopDashboardd.png) |

| Mobile Dashboard | Mobile More |
|:-:|:-:|
| ![](frontend/public/screenshots/mobile-dashboardd.jpg) | ![](frontend/public/screenshots/mobile-more.jpg) |

---

## Features

- **Dashboard** — Readiness score, GitHub-style heatmap, weekly activity chart, company progress, streak tracking
- **DSA Tracker** — Problem library with filters, tags, difficulty badges, revision status, and stats
- **Companies** — Track applications, deadlines, company-specific checklists, cluster filters (FAANG, Product, etc.)
- **Resumes** — PDF upload with validation, keyword extraction, scoring, active-resume management
- **Calendar** — Milestone and deadline overview
- **Analytics** — Cross-section breakdowns and trends
- **Notes & Resources** — Personal notes and link collections
- **Settings** — Profile and preferences
- **Command Palette** — Press `⌘K` / `Ctrl+K` to search across companies, problems, notes, and resources instantly

### Mobile Navigation

OfferForge uses a bottom tab bar on phones (5 primary tabs + a **More** grid page for remaining sections), avoiding overlay drawers that block content.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS v4, Recharts, TanStack Query, Lucide Icons |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, Google OAuth |
| **Database** | PostgreSQL 16 (asyncpg) |
| **Storage** | Cloudinary (resume PDFs) |

---

## Quickstart

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your secrets (JWT, Cloudinary, Google OAuth)

# 2. Launch everything
docker compose up --build
```

| Service | URL |
| :--- | :--- |
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/    # AppLayout, Topbar, Sidebar (desktop), CommandPalette
│   │   ├── ui/        # shadcn-inspired primitives
│   │   └── shared/    # EmptyState, AuthCard, ProtectedRoute
│   ├── pages/         # Dashboard, Companies, DSA, Notes, More, …
│   ├── api/           # API client modules
│   ├── context/       # Auth, Theme
│   └── lib/           # Utilities, chart theme
├── backend/
│   ├── app/
│   │   ├── api/       # Route definitions
│   │   ├── core/      # Config, security, dependencies
│   │   ├── models/    # SQLAlchemy models
│   │   └── schemas/   # Pydantic schemas
│   └── alembic/       # Migrations
```

---

## License

[MIT](LICENSE)
