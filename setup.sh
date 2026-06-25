#!/usr/bin/env bash
# Quick setup: export from Access DB and import into SQLite
# Usage: ./setup.sh "path/to/EQ Projekty.accdb"

set -e

DB="${1:-/tmp/eq_db_extracted/EQ Projekty_23.03.accdb}"

if [ ! -f "$DB" ]; then
  echo "ERROR: File not found: $DB"
  echo "Usage: $0 <path-to-accdb>"
  exit 1
fi

# Check for mdbtools
if ! command -v mdb-export &>/dev/null; then
  echo "ERROR: mdbtools is not installed."
  echo ""
  echo "Install it with:"
  echo "  Ubuntu/Debian:  sudo apt-get install mdbtools"
  echo "  macOS:          brew install mdbtools"
  echo "  Fedora/RHEL:    sudo dnf install mdbtools"
  echo ""
  exit 1
fi

echo "Exporting tables from Access database..."
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
mdb-export "$DB" "JazykyIQK"             > /tmp/jazyky_iqk.csv
mdb-export "$DB" "Hviezdicky"            > /tmp/hviezdicky.csv
mdb-export "$DB" "TestPolozky"           > /tmp/testpolozky.csv

echo "Importing into SQLite..."
python import_data.py

echo ""
echo "Done! Start the server with:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
