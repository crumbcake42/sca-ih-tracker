# Default: show available commands
default:
    @just --list

# ── Backend ──────────────────────────────────────────────────
# Start FastAPI dev server. Pass log=true to enable SQL query logging.
api log="":
    cd backend && LOG_SQL={{log}} .venv/Scripts/uvicorn app.main:app --reload

# Initialize DB, run migrations, seed data
seed:
    cd backend && .venv/Scripts/setup-db

# Lint project with ruff
ruff:
    cd backend && .venv/Scripts/ruff check

# Lint project with ruff and fix fixable errors
ruff-fix:
    cd backend && .venv/Scripts/ruff check --fix

# Run all tests
test:
    cd backend && .venv/Scripts/pytest

# Run tests with coverage
test-cov:
    cd backend && .venv/Scripts/pytest --cov

# Create a new migration (usage: just migrate "add rfas table")
migrate msg:
    cd backend && .venv/Scripts/alembic revision --autogenerate -m "{{msg}}"

# Apply all pending migrations
upgrade:
    cd backend && .venv/Scripts/alembic upgrade head

# ── Frontend ─────────────────────────────────────────────────
# Start Vite dev server
ui:
    cd frontend && npm run dev

# ── Combined ─────────────────────────────────────────────────
# Start both servers. Pass log=true to enable SQL query logging.
dev log="":
    cd backend && LOG_SQL={{log}} .venv/Scripts/uvicorn app.main:app --reload &
    cd frontend && npm run dev
