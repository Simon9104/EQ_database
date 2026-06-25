# EQ Projekty – Web Application

Modern web reimplementation of the EQ Projekty Access database, built with FastAPI + SQLite + vanilla JS.

## Features

All features from the original Access database are preserved:

- **Projekty** – project list with full filtering (status, manager, flags), detail view with tabs (basic info, items, notes, log), create/edit/delete
- **Položky** – line items per project with printing parameters (format, binding, paper, FAR/CB pages), pricing with discount and VAT calculation
- **Faktúry** – invoice list with overdue highlighting, totals, paid/unpaid filter
- **Zákazníci** – customer address book
- **Bankové pohyby** – bank transaction ledger (OFX/CREDIT/DEBIT)
- **Vyradovanie** – imposition calculation records
- **Nastavenia** – manage all lookup tables (project statuses, order types, bindings, VAT rates, etc.)

## Tech Stack

- **Backend**: Python 3.11 + FastAPI + SQLAlchemy (async) + aiosqlite
- **Database**: SQLite (`eq_database.db`)
- **Frontend**: Vanilla JS SPA served from FastAPI static files

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Export data from the Access .accdb file (requires mdbtools)
#    Replace the path with your actual .accdb file
DB="path/to/EQ Projekty_23.03.accdb"
mdb-export "$DB" "DocasnaTabulkaProjekty" > /tmp/projects.csv
mdb-export "$DB" "DocasnaTabulkaPolozky"  > /tmp/polozky.csv
mdb-export "$DB" "DocasnaTabulkaZoznamFa" > /tmp/faktury.csv
mdb-export "$DB" "DocasnaTabulkaAdresy"   > /tmp/adresy.csv
mdb-export "$DB" "DocasnaTabulkaKredity"  > /tmp/kredity.csv
mdb-export "$DB" "Vyradovanie"            > /tmp/vyradovanie.csv
mdb-export "$DB" "StavProjektov"          > /tmp/stavy.csv
mdb-export "$DB" "Status polozky"         > /tmp/status_polozky.csv
mdb-export "$DB" "Typ zakazky"            > /tmp/typ_zakazky.csv
mdb-export "$DB" "PovrchovaUprava"        > /tmp/povrch.csv
mdb-export "$DB" "User"                   > /tmp/users.csv
mdb-export "$DB" "Podfilter projektov"    > /tmp/podfilter.csv
mdb-export "$DB" "TypOdmenyIQK"           > /tmp/typ_odmeny.csv
mdb-export "$DB" "Sadzba DPH"             > /tmp/dph.csv
mdb-export "$DB" "Vazby"                  > /tmp/vazby.csv

# 3. Import into SQLite
python import_data.py

# 4. Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 in your browser.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/projects` | List / create projects |
| GET/PUT/DELETE | `/api/projects/{id}` | Get / update / delete project |
| GET/POST | `/api/projects/{id}/items` | List / add items for a project |
| GET | `/api/items` | List all items (with filters) |
| PUT/DELETE | `/api/items/{id}` | Update / delete item |
| GET/POST | `/api/invoices` | List / create invoices |
| GET/PUT/DELETE | `/api/invoices/{id}` | Invoice detail |
| GET/POST | `/api/customers` | Customers |
| GET/POST | `/api/credits` | Bank transactions |
| GET/POST | `/api/imposition` | Imposition records |
| GET | `/api/lookups` | All lookup tables in one call |
