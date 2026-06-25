# EQ Projekty – Administrátorská príručka

---

## 1. Prvé spustenie

### Inštalácia

```bash
pip install -r requirements.txt
```

### Spustenie servera

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Aplikácia beží na http://localhost:8000. Pre prístup z iných počítačov v sieti použite IP adresu servera: `http://192.168.x.x:8000`

### Prvé prihlásenie

Pri prvom štarte server automaticky nastaví **prvého používateľa** v databáze ako admina s heslom `admin`. V termináli uvidíte:
```
[AUTH] Default admin set: username='Lu' password='admin'
```

**Ihneď po prihlásení zmeňte heslo:** Nastavenia → Zmena hesla.

### Import dát z Access databázy (jednorazovo)

Vyžaduje `mdbtools`:
```bash
sudo apt-get install mdbtools   # Ubuntu/Debian
brew install mdbtools            # macOS

./setup.sh "cesta/k/EQ Projekty.accdb"
```

---

## 2. Správa používateľov (cez terminál servera)

Všetka správa používateľov sa robí priamo cez SQLite na serveri. Vlastné heslo si každý používateľ môže zmeniť sám cez web (Nastavenia → Zmena hesla).

### Zobrazenie všetkých používateľov

```bash
sqlite3 eq_database.db "SELECT id, username, plne_meno, is_admin, active, password_hash IS NOT NULL as ma_heslo FROM users;"
```

### Nastavenie hesla používateľovi

Heslo sa musí zaheslovať — použite tento Python príkaz priamo na serveri:

```bash
python3 - <<'EOF'
import bcrypt, sys
username = input("Username: ")
password = input("Nové heslo: ")
h = bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()

import sqlite3
con = sqlite3.connect("eq_database.db")
con.execute("UPDATE users SET password_hash=? WHERE username=?", (h, username))
con.commit()
rows = con.execute("SELECT changes()").fetchone()[0]
con.close()
print(f"Aktualizovaných riadkov: {rows}")
EOF
```

Alebo ako jednoriadkový skript (zadajte priamo):
```bash
python3 -c "
import bcrypt, sqlite3, getpass
u = input('Username: ')
p = getpass.getpass('Heslo: ')
h = bcrypt.hashpw(p.encode()[:72], bcrypt.gensalt()).decode()
con = sqlite3.connect('eq_database.db')
con.execute('UPDATE users SET password_hash=? WHERE username=?', (h,u))
con.commit(); con.close(); print('Hotovo')
"
```

### Zmena username

```bash
sqlite3 eq_database.db "UPDATE users SET username='nové_meno' WHERE username='staré_meno';"
```

Používateľ sa musí odhlásiť a znova prihlásiť s novým menom.

### Udelenie admin práv

```bash
sqlite3 eq_database.db "UPDATE users SET is_admin=1 WHERE username='meno';"
```

### Odobratie admin práv

```bash
sqlite3 eq_database.db "UPDATE users SET is_admin=0 WHERE username='meno';"
```

### Aktivácia / deaktivácia používateľa

```bash
# Deaktivácia – používateľ sa nemôže prihlásiť
sqlite3 eq_database.db "UPDATE users SET active=0 WHERE username='meno';"

# Aktivácia
sqlite3 eq_database.db "UPDATE users SET active=1 WHERE username='meno';"
```

### Núdzový reset hesla (ak sa nikto nevie prihlásiť)

```bash
sqlite3 eq_database.db "UPDATE users SET password_hash=NULL WHERE id=1;"
```
Reštartujte server — heslo prvého používateľa sa automaticky resetuje na `admin`.

### Zmena vlastného hesla (web)

Každý prihlásený používateľ si môže zmeniť heslo sám: **Nastavenia → Zmena hesla**

---

## 3. Práca s projektmi

### Zoznam projektov

**Projekty** — hlavný modul. Zoznam obsahuje:
- Filtrovanie podľa stavu, manažéra, kategórie, obdobia
- Globálne vyhľadávanie (lupa v topbare)
- Farebné odznaky stavov
- Export do CSV (tlačidlo ↓ Export CSV)

### Vytvorenie projektu

1. Kliknite **+ Pridať**
2. Vyplňte povinné polia:
   - **Názov projektu**
   - **Firma** (odberateľ)
   - **Manažér**
   - **Stav** (napr. Očakávaný)
3. Voliteľné: termín, cena, poznámky, príznaky (F1–F4), podobný projekt
4. Kliknite **Uložiť**

### Detail projektu

Kliknite na riadok projektu. Otvorí sa panel vpravo so záložkami:

| Záložka | Obsah |
|---------|-------|
| **Základné** | Všetky polia projektu |
| **Položky** | Tlačové položky (knižky, letáky...) |
| **Náklady** | Náklady na subdodávateľov |
| **Poznámky** | Interné poznámky |
| **Log** | História zmien |

> Ak má projekt otvorený aj iný používateľ, zobrazí sa žltý banner s jeho menom.

### Úprava projektu

V detaile kliknite **✏️ Upraviť** → zmeňte polia → **Uložiť**

### Vymazanie projektu

Upraviť → červené tlačidlo **🗑 Odstrániť** (nevratná akcia)

---

## 4. Práca s položkami

Položky sú tlačové zákazky viazané na projekt (napr. konkrétna kniha, leták).

### Pridanie položky k projektu

1. Otvorte detail projektu → záložka **Položky**
2. Kliknite **+ Pridať položku**
3. Vyplňte parametre tlače:
   - Formát, počet strán, náklad
   - Väzba, papier, povrchová úprava
   - FAR/CB strany, cena

### Záložky v detaile položky

| Záložka | Obsah |
|---------|-------|
| **Základné** | Názov, stav, ceny, zisk |
| **Tlač** | Parametre tlače (formát, väzba, papier...) |
| **Poznámky** | Interné poznámky k položke |

### Zoznam všetkých položiek

**Položky** v menu — zobrazuje všetky položky naprieč projektmi s filtrovaním.

---

## 5. Práca s faktúrami

### Zoznam faktúr

**Faktúry** — zobrazuje všetky vystavené faktúry:
- Červené riadky = faktúra po splatnosti
- Stĺpec **Zostáva** = neuhradená suma
- Filter: všetky / uhradené / neuhradené / po splatnosti

### Vytvorenie faktúry

1. Kliknite **+ Pridať**
2. Vyplňte:
   - **Číslo faktúry** (variabilný symbol pre platbu)
   - **Odberateľ**, dátum vystavenia, splatnosť
   - Sumy: bez DPH, s DPH, k úhrade
3. **Uložiť**

### Označenie faktúry ako uhradenej

Buď manuálne (Upraviť → vyplniť Dátum úhrady, Zostáva = 0), alebo automaticky cez **Párovanie faktúr** (viď sekcia 7).

### Export faktúr

Topbar → **↓ Export CSV**

---

## 6. Práca s firmami

**Firmy** — adresár odberateľov a dodávateľov.

### Typy firiem

| Príznak | Popis |
|---------|-------|
| Odberateľ | Klient, ktorý si objednáva tlač |
| Dodávateľ | Subdodávateľ (tlačiareň, grafik...) |
| Agentúra | Reklamná agentúra |

### Vytvorenie firmy

**+ Pridať** → vyplniť IČO, DIČ, IČ DPH, adresu, bankový účet → **Uložiť**

### Kontakty k firme

V detaile firmy → záložka **Kontakty** → **+ Pridať kontakt**

---

## 7. Bankové pohyby a párovanie faktúr

### Import bankového výpisu

**Bankové pohyby → Import výpisu**

**OFX (odporúčané):**
1. Prihláste sa do internet bankingu (Tatra banka, VÚB, ČSOB, Sporiteľňa)
2. Exportujte výpis vo formáte OFX/QFX
3. Nahrajte súbor → **Importovať OFX**
4. Duplikáty sú automaticky preskočené

**PDF:**
1. Nahrajte PDF výpis z banky → **Importovať PDF**
2. Transakcie sú extrahované automaticky
3. PDF je menej spoľahlivý — uprednostnite OFX

### Párovanie faktúr s platbami

**Bankové pohyby → Párovanie faktúr**

Systém párovanie robí cez **variabilný symbol (VS)**:
- VS v bankovom pohybe = číslo faktúry

Postup:
1. **Náhľad párovania** — skontrolujte navrhované zhody bez zmien
2. **Spárovať a aktualizovať faktúry** — aplikuje zmeny:
   - Zníži zostatok faktúry o sumu platby
   - Nastaví dátum úhrady ak zostatok = 0
3. **Spárovať ručne** — pre platby bez VS zadajte číslo faktúry ručne

---

## 8. IQK – Informačný systém knižnej kultúry

Evidencia kníh pre register knižnej kultúry.

### Produkty (knihy)

**IQK** → zoznam kníh s ISBN, autorom, vydavateľom, počtom strán, nákladom, cenami.

### Transakcie

K každej knihe sa evidujú transakcie: predaj, vrátenie, odmena. V detaile produktu → záložka **Transakcie** → **+ Transakcia**

---

## 9. Nastavenia číselníkov

**Nastavenia** — správa všetkých rozbaľovacích zoznamov v aplikácii.

| Číselník | Kde sa používa |
|----------|----------------|
| Stavy projektov | Stav projektu (Očakávaný, Prebiehajúci...) |
| Status položky | Stav tlačovej položky |
| Typy zákaziek | Kategória zákazky |
| Typy odmien | IQK odmeny |
| Typy nákladov | Kategórie nákladov |
| Podfiltre projektov | Podkategórie filtrovania |
| Väzby | Knižná väzba (V1, V2, brož...) |
| Povrchová úprava | Lesklé lamino, matné lamino... |
| Sadzby DPH | Napr. 0.1 = 10 %, 0.2 = 20 % |
| Ceny obálky (JCV) | Jednotkové ceny výroby obálky |
| Jazyky IQK | Jazyky pre IQK register |

### Pridanie / úprava / vymazanie hodnoty

Pri každom číselníku: upravte pole → 💾 uložiť, alebo 🗑 vymazať. Tlačidlo **+ Pridať** pridá nový riadok.

---

## 10. Zálohovanie databázy

Celá databáza je jeden súbor `eq_database.db`.

```bash
# Manuálna záloha
cp eq_database.db eq_database_$(date +%Y%m%d).db

# Automatická denná záloha (crontab)
0 2 * * * cp /cesta/eq_database.db /zalohy/eq_database_$(date +\%Y\%m\%d).db

# Obnova zo zálohy
cp eq_database_20240101.db eq_database.db
```

---

## 11. Priame operácie s databázou (SQLite)

Pre pokročilé operácie priamo cez príkazový riadok:

```bash
# Otvorenie databázy
sqlite3 eq_database.db

# Zoznam tabuliek
.tables

# Zoznam používateľov
SELECT id, username, plne_meno, is_admin, active FROM users;

# Počet projektov podľa stavu
SELECT stav, COUNT(*) FROM projekty GROUP BY stav;

# Neuhradené faktúry
SELECT cislo_faktury, odberatel, zostava_uhradit, datum_splatnosti
FROM faktury WHERE zostava_uhradit > 0 ORDER BY datum_splatnosti;

# Faktúry po splatnosti
SELECT cislo_faktury, odberatel, zostava_uhradit, dni_po_splatnosti
FROM faktury WHERE dni_po_splatnosti > 0 AND zostava_uhradit > 0;

# Suma neuhradených faktúr
SELECT SUM(zostava_uhradit) FROM faktury WHERE zostava_uhradit > 0;

# Projekty bez faktúry (na fakturáciu)
SELECT id, nazov_projektu, nazov_firmy FROM projekty WHERE stav = 'Fakturovať';

# Ukončenie sqlite3
.quit
```

---

## 12. Premenné prostredia

| Premenná | Popis | Predvolená hodnota |
|----------|-------|--------------------|
| `EQ_SECRET_KEY` | Tajný kľúč pre JWT — **zmeňte v produkcii** | `eq-projekty-secret-change-in-production-2024` |

```bash
export EQ_SECRET_KEY="vas-dlhy-nahodny-kluc-min-32-znakov"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 13. Riešenie problémov

| Problém | Riešenie |
|---------|----------|
| `ModuleNotFoundError: No module named 'bcrypt'` | `pip install bcrypt` |
| `ModuleNotFoundError: No module named 'jose'` | `pip install python-jose[cryptography]` |
| `no such column: users.password_hash` | Server je starý — reštartujte, migrácia sa spustí automaticky |
| 401 Unauthorized pri prihlásení | Skontrolujte username cez `sqlite3 eq_database.db "SELECT username FROM users;"` |
| Zabudnuté heslo admina | Viď sekcia 2 — Núdzový reset hesla |
| Server neodpovedá | Skontrolujte či beží: `ps aux | grep uvicorn` |
