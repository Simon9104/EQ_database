# EQ Projekty – Administrátorská príručka

## Prvé spustenie

1. Nainštalujte závislosti:
   ```bash
   pip install -r requirements.txt
   ```

2. Spustite server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. Pri prvom štarte server automaticky nastaví **prvého používateľa** v databáze ako admina s heslom `admin`. V termináli uvidíte:
   ```
   [AUTH] Default admin set: username='Lu' password='admin'
   ```

4. Otvorte http://localhost:8000 a prihláste sa.

5. **Ihneď zmeňte heslo:** Nastavenia → Zmena hesla.

---

## Správa používateľov

Prístupné cez **Nastavenia → Správa používateľov** (len pre admina).

| Akcia | Popis |
|-------|-------|
| **Nastaviť heslo** | Nastaví heslo ľubovoľnému používateľovi (min. 4 znaky) |
| **Admin: Pridať/Odobrať** | Prepína admin práva |
| **Aktivovať / Deaktivovať** | Deaktivovaný používateľ sa nemôže prihlásiť |

Používatelia sú importovaní z pôvodnej Access databázy (tabuľka `User`). Všetci začínajú bez hesla — admin im musí heslo nastaviť, kým sa môžu prihlásiť.

### Zmena vlastného hesla

Nastavenia → Zmena hesla → zadajte staré heslo, nové heslo, zopakovať → **Zmeniť heslo**.

### Reset hesla cez SQLite (núdzový prípad)

Ak sa nikto nevie prihlásiť:
```bash
# Zobrazí zoznam používateľov
sqlite3 eq_database.db "SELECT id, username, is_admin, active FROM users;"

# Vymaže heslo prvého admina (server ho pri reštarte nastaví na 'admin')
sqlite3 eq_database.db "UPDATE users SET password_hash=NULL WHERE id=1;"
```
Potom reštartujte server.

---

## Import dát z Access databázy

Jednorazový import pri prvom nasadení (vyžaduje `mdbtools`):

```bash
# Ubuntu/Debian
sudo apt-get install mdbtools

# macOS
brew install mdbtools

# Spustite import
./setup.sh "cesta/k/EQ Projekty.accdb"
```

Skript exportuje všetky tabuľky do `/tmp/*.csv` a spustí `python import_data.py`.

---

## Import bankového výpisu

**Bankové pohyby → Import výpisu**

### OFX (odporúčané)
- Exportujte OFX súbor z internet bankingu (Tatra banka, VÚB, ČSOB, Slovenská sporiteľňa)
- Nahrajte cez **Import výpisu → OFX súbor → Importovať OFX**
- Duplikáty sú automaticky preskočené

### PDF
- Nahrajte PDF výpis z banky
- Transakcie sú extrahované automaticky (variabilný symbol, suma, dátum)
- PDF import je menej spoľahlivý ako OFX — pri problémoch použite OFX export z banky

---

## Párovanie faktúr s platbami

**Bankové pohyby → Párovanie faktúr**

1. **Náhľad párovania** — zobrazí zoznam spárovaných a nespárovaných platieb bez zmien v databáze
2. **Spárovať a aktualizovať faktúry** — aplikuje párovanie:
   - Zníži `zostava_uhradit` faktúry o sumu platby
   - Nastaví `datum_uhrady` ak zostatok = 0
   - Prepočíta `dni_po_splatnosti`
3. **Spárovať ručne** — pre nespárované platby zadajte číslo faktúry manuálne

Párovanie funguje cez **variabilný symbol (VS)**: `trnvasym` v bankovom pohybe = `cislo_faktury` vo faktúre.

---

## Nastavenia číselníkov

**Nastavenia** obsahuje správu všetkých číselníkov:

| Číselník | Popis |
|----------|-------|
| Stavy projektov | Napr. Očakávaný, Prebiehajúci, Ukončený |
| Status položky | Stavy tlačových položiek |
| Typy zákaziek | Druh zákazky |
| Typy odmien | Pre IQK odmeny |
| Typy nákladov | Kategórie nákladov na projektoch |
| Podfiltre projektov | Podkategórie pre filtrovanie |
| Väzby | Typy knižnej väzby (kód + popis) |
| Povrchová úprava | Napr. lesklé lamino, matné lamino |
| Sadzby DPH | Percentuálne sadzby (napr. 0.1 = 10 %) |
| Ceny obálky (JCV) | Jednotkové ceny výroby obálky |
| Jazyky IQK | Jazyky pre IQK register |

---

## Zálohovanie

Celá databáza je jeden súbor:

```bash
# Záloha
cp eq_database.db eq_database_$(date +%Y%m%d).db

# Obnova
cp eq_database_20240101.db eq_database.db
```

---

## Premenné prostredia

| Premenná | Popis | Predvolená hodnota |
|----------|-------|--------------------|
| `EQ_SECRET_KEY` | Tajný kľúč pre JWT tokeny — **zmeňte pred produkciou** | `eq-projekty-secret-change-in-production-2024` |

```bash
export EQ_SECRET_KEY="vas-tajny-kluc-min-32-znakov"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
