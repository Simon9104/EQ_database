# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server (development)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Import data from Access .accdb (requires mdbtools)
./setup.sh "path/to/EQ Projekty.accdb"
# Then:
python import_data.py

# Check JS syntax
node --check static/app.js

# Direct DB inspection
sqlite3 eq_database.db "SELECT ..."
```

## Architecture

**Single-file SPA + FastAPI backend.** The frontend is a vanilla JS SPA (`static/app.js`, ~2200 lines) served directly by FastAPI. There is no build step. All views, state, and API calls live in `app.js`.

### Backend (`app/`)

- `main.py` — FastAPI app, lifespan (runs `init_db` + `ensure_default_admin`), exports `/api/dashboard`, `/api/export/*`, serves `static/index.html` (auth-guarded) and `static/login.html`
- `database.py` — async SQLAlchemy engine + `init_db()` which runs `create_all` and inline `ALTER TABLE` migrations for schema changes on existing DBs
- `models.py` — all ORM models in one file (Project, Item, Invoice, Credit, Customer, Imposition, Firma, Kontakt, Naklad, IQKProdukt, IQKTransakcia, all lookup tables, User)
- `routers/` — one file per domain: `projects`, `items`, `invoices`, `customers`, `credits`, `firmy`, `kontakty`, `naklady`, `iqk`, `bank`, `imposition`, `lookups`, `auth`

**Lookup tables** are all served in a single `GET /api/lookups` call at app init. Individual CRUD routers for each lookup are generated via `make_crud()` in `lookups.py`.

**Auth** (`routers/auth.py`): cookie-based JWT (8h), `bcrypt` for hashing (no passlib — incompatible with bcrypt ≥ 4.0). On startup, if no user has a password, the first user in the `users` table is set as admin with password `admin`. The `User` model has `password_hash`, `is_admin`, `active` columns added via inline migration in `init_db`.

**Bank import** (`routers/bank.py`): parses OFX (SGML-style Slovak bank format) and PDFs via `pdfplumber`. Matches CREDIT transactions to invoices by variable symbol (`trnvasym` → `cislo_faktury`). Updates `zostava_uhradit`, `datum_uhrady`, `dni_po_splatnosti` on matched invoices.

### Frontend (`static/`)

- `app.js` — all logic: `API` object (auto-redirects 401 → `/login`), `State`, `App`, `Views` (one object per view), utility functions
- `index.html` — shell with sidebar nav, topbar, `#content` div, detail panel, modal overlay
- `login.html` — standalone login page (no app.js dependency)
- `style.css` — all styles

**View pattern:** each `Views.<name>` has `render()`, `load()`, `openDetail()`, `openAdd()`, `openEdit()`, `save()`, `delete()`. `App.navigate(view)` calls `render()`. The settings view is patched after definition to inject additional sections (PovrchovaUprava, JazykyIQK, user management).

**Lookups** are loaded once at init into `State.lookups` and used to populate dropdowns throughout the app.

### Database

SQLite file: `eq_database.db`. Original data comes from an MS Access `.accdb` file exported with `mdbtools`. The `DocasnaTabulka*` tables in the original Access DB are temporary export snapshots — the real linked tables were rebuilt from scratch in SQLite.

### Adding a new entity

1. Add model to `app/models.py`
2. Add router in `app/routers/` (or use `make_crud()` for simple lookup tables)
3. Register router in `app/main.py`
4. Add `ALTER TABLE` migration in `database.py` `init_db()` if adding columns to existing tables
5. Add `Views.<name>` object in `static/app.js` with `render/load/openDetail/openForm/save/delete`
6. Add sidebar nav entry in `static/index.html` and title in the `titles` map in `app.js`
