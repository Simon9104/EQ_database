"""Import data from mdb-export CSV files into SQLite."""
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "eq_database.db"

def parse_bool(v):
    if v is None or v == "":
        return False
    return str(v).strip() in ("1", "True", "true", "Yes")

def parse_float(v):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return None

def parse_int(v):
    if v is None or v == "":
        return None
    try:
        return int(float(str(v)))
    except Exception:
        return None

def parse_date(v):
    if not v or str(v).strip() == "":
        return None
    for fmt in ("%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(str(v).strip(), fmt).isoformat()
        except Exception:
            pass
    return None

def read_csv(path):
    p = Path(path)
    if not p.exists():
        print(f"  SKIP (not found): {path}")
        return []
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Projects
    print("Importing projects...")
    rows = read_csv("/tmp/projects.csv")
    for r in rows:
        c.execute("""INSERT OR REPLACE INTO projekty (
            id, nazov_projektu, nazov_firmy, priezvisko_meno, manazer, kategoria,
            priorita, stav, f1, f2, f3, f4, stav2, stav3, force, prijate, prijal,
            termin_odovzdania, zostava, poznamky, poznamky_zl, poznamky_1,
            poznamka_cp, folder_zakazky, folder_cp, cislo_objednavky,
            datum_prijatia_objednavky, datum_na_objednavke,
            cena_bez_dph, dph_ceny, cena_s_dph, naklady, zisk,
            cena_bez_fa, naklady_bez_fa,
            vpt_agenturnacena, projekt_expedovat, projekt_expedovat_datum,
            projekt_oznaceny, projekt_kreditny, projekt_zberny,
            projekt_fakturovany, projekt_fakturovany_vopred, projekt_uhradeny,
            projekt_cp, projekt_sledovany, projekt_kniha, projekt_cakajuci,
            projekt_bezny, projekt_hotovo,
            kredit, zucastneni, strucna_specifikacia, cislo_cp, podobny_projekt, projekt_log
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            parse_int(r.get("ID")),
            r.get("Názov projektu", ""),
            r.get("Názov firmy", ""),
            r.get("Priezvisko a meno", ""),
            r.get("Manažér", ""),
            r.get("Kategória", ""),
            r.get("Priorita", ""),
            r.get("Stav", ""),
            r.get("F1", ""), r.get("F2", ""), r.get("F3", ""), r.get("F4", ""),
            r.get("Stav2", ""), r.get("Stav3", ""),
            parse_bool(r.get("Force")),
            parse_date(r.get("Prijaté")),
            r.get("Prijal", ""),
            parse_date(r.get("TerminOdovzdania")),
            r.get("Zostáva", ""),
            r.get("Poznámky", ""), r.get("Poznámky v ZL", ""), r.get("Poznámky 1", ""),
            r.get("Poznámka CP", ""),
            r.get("Folder zakazky", ""), r.get("Folder CP", ""),
            r.get("Číslo objednávky", ""),
            parse_date(r.get("DatumPrijatiaObjednavky")),
            parse_date(r.get("DatumNaObjednavke")),
            parse_float(r.get("Cena projektu bez DPH")),
            parse_float(r.get("DPH ceny projektu")),
            parse_float(r.get("Cena projektu s DPH")),
            parse_float(r.get("Náklady projektu")),
            parse_float(r.get("Zisk projektu")),
            parse_float(r.get("CenaProjektuBezFa")),
            parse_float(r.get("NakladyProjektuBezFa")),
            parse_bool(r.get("VpTAgenturnaCena")),
            parse_bool(r.get("ProjektExpedovat")),
            parse_date(r.get("ProjektExpedovatDatum")),
            parse_bool(r.get("ProjektOznaceny")),
            parse_bool(r.get("ProjektKreditny")),
            parse_bool(r.get("ProjektZberny")),
            parse_bool(r.get("ProjektFakturovany")),
            parse_bool(r.get("ProjektFakturovanyVopred")),
            parse_bool(r.get("ProjektUhradeny")),
            parse_bool(r.get("ProjektCP")),
            parse_bool(r.get("ProjektSledovany")),
            parse_bool(r.get("ProjektKniha")),
            parse_bool(r.get("ProjektCakajuci")),
            parse_bool(r.get("ProjektBezny")),
            parse_bool(r.get("ProjektHotovo")),
            parse_float(r.get("Kredit")),
            r.get("Zucastneni", ""),
            r.get("StrucnaSpecifikacia", ""),
            r.get("CisloCP", ""),
            r.get("PodobnyProjekt", ""),
            r.get("ProjektLog", ""),
        ))
    conn.commit()
    print(f"  {len(rows)} projects imported")

    # Items
    print("Importing items...")
    rows = read_csv("/tmp/polozky.csv")
    for r in rows:
        c.execute("""INSERT OR REPLACE INTO polozky (
            id, poradie, id_projektu, popis, podpopis, strucna_specifikacia,
            mj, pocet, jc, cena, zlava, sadzba_dph, cena_s_dph,
            status, typ_zakazky, polozka_pracuje,
            fakturovat, fakturovane, faktura_vopred, do_faktury,
            kto_fakturuje, datum_fakturacie, cislo_faktury, id_faktury,
            poznamka, poznamka_vl,
            vyber_x, polozka_x, dl, objednavka_x, cp_polozky_x, odovzdane,
            typ_kalkulacie, pocet_stran, pocet_stran_far, format, vazba,
            db_vn_papier_typ, db_vn_papier_lesk_mat, db_vn_papier_specifikacia,
            db_ob_farebnost, db_ob_papier_typ, db_ob_papier_lesk_mat,
            db_ob_pu, db_ob_pu_skratka, db_chrbat, db_lacetka,
            format_th, far_strany, cb_klikov_na_far_spolu, pocet_sad,
            klikov_na_far_spolu, far_klikov, vkladacky_ano_nie, vkladacky_text,
            pocet_th_obalky, ako_vkladat, na_far,
            pdftk_cb_tlac, pdftk_vkladacky, pdftk_komplet, pdftk_komplet_kratky,
            cb_strany_pocet, cb_strany, cb_na_cb_pocet, cb_na_far_pocet,
            na_cb_pocet, far_strany_pocet, na_far_pocet, klk_na_cb,
            polozka_expedovat, polozka_expedovat_datum, komu_dodat,
            polozka_kde_vyzdvihnut, filter_vazba_retazec, zhrnuty_text_vyradovaca, id_produktu_db
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            parse_int(r.get("PolozkaID")),
            parse_int(r.get("PolozkaPoradie")),
            parse_int(r.get("IDProjektu")),
            r.get("Popis", ""),
            r.get("Podpopis", ""),
            r.get("StrucnaSpecifikacia", ""),
            r.get("mj", ""),
            parse_float(r.get("Počet")),
            parse_float(r.get("jc")),
            parse_float(r.get("Cena")),
            parse_float(r.get("Zľava")),
            parse_float(r.get("SadzbaDPH")),
            parse_float(r.get("Cena_s_DPH")),
            r.get("Status", ""),
            r.get("TypZakazky", ""),
            r.get("Polozka_pracuje", ""),
            parse_bool(r.get("Fakturovať")),
            parse_bool(r.get("Fakturované")),
            parse_bool(r.get("Faktúra vopred")),
            parse_bool(r.get("DoFaktury")),
            r.get("Kto fakturuje", ""),
            parse_date(r.get("Dátum fakturácie")),
            r.get("Číslo faktúry", ""),
            r.get("IDFaktury", ""),
            r.get("Poznámka", ""),
            r.get("PoznamkaVL", ""),
            parse_bool(r.get("VyberX")),
            parse_bool(r.get("PolozkaX")),
            parse_bool(r.get("DL")),
            parse_bool(r.get("ObjednavkaX")),
            parse_bool(r.get("CPPolozkyX")),
            parse_bool(r.get("Odovzdane")),
            r.get("TypKalkulacie", ""),
            parse_int(r.get("PocetStran")),
            parse_int(r.get("PocetStranFAR")),
            r.get("Format", ""),
            r.get("Vazba", ""),
            r.get("DB_vn_papier_typ", ""),
            r.get("DB_vn_papier_lesk_mat", ""),
            r.get("DB_vn_papier_specifikacia", ""),
            r.get("DB_ob_farebnost", ""),
            r.get("DB_ob_papier_typ", ""),
            r.get("DB_ob_papier_lesk_mat", ""),
            r.get("DB_ob_pu", ""),
            r.get("DB_ob_pu_skratka", ""),
            r.get("DB_chrbat", ""),
            r.get("DB_lacetka", ""),
            r.get("FormatTH", ""),
            r.get("FARstrany", ""),
            parse_int(r.get("CBKlikovNaFARSpolu")),
            parse_int(r.get("PocetSad")),
            parse_int(r.get("KlikovNaFARSpolu")),
            parse_int(r.get("FARKlikov")),
            parse_bool(r.get("VkladackyAnoNie")),
            r.get("VkladackyText", ""),
            r.get("PocetTHObalky", ""),
            r.get("AkoVkladat", ""),
            r.get("NaFAR", ""),
            r.get("PDFTKstringCBtlac", ""),
            r.get("PDFTKstringVkladacky", ""),
            r.get("PDFTKstringKomplet", ""),
            r.get("PDFTKstringKompletKratky", ""),
            r.get("CBstranyPocet", ""),
            r.get("CBstrany", ""),
            r.get("CBnaCBPocet", ""),
            r.get("CBnaFARPocet", ""),
            r.get("naCBPocet", ""),
            r.get("FARstranyPocet", ""),
            r.get("NaFARPocet", ""),
            r.get("klkNaCB", ""),
            parse_bool(r.get("PolozkaExpedovat")),
            parse_date(r.get("PolozkaExpedovatDatum")),
            r.get("KomuDodat", ""),
            r.get("PolozkaKdeVyzdvihnúť", ""),
            r.get("FilterVazbaRetazec", ""),
            r.get("ZhrnutyTextVyradovacaDoDB", ""),
            parse_int(r.get("IDproduktuDB")),
        ))
    conn.commit()
    print(f"  {len(rows)} items imported")

    # Invoices
    print("Importing invoices...")
    rows = read_csv("/tmp/faktury.csv")
    for i, r in enumerate(rows, 1):
        c.execute("""INSERT OR REPLACE INTO faktury (
            id, cislo_faktury, datum_vystavenia, odberatel, popis,
            suma_bez_dph, suma_s_dph, suma_k_uhrade, datum_splatnosti,
            zostava_uhradit, dni_po_splatnosti, datum_uhrady
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
            parse_int(r.get("FaID")) or i,
            r.get("Číslo faktúry", ""),
            parse_date(r.get("Dátum vystavenia")),
            r.get("Odberateľ", ""),
            r.get("Popis", ""),
            parse_float(r.get("Suma bez DPH")),
            parse_float(r.get("Suma s DPH")),
            parse_float(r.get("Suma k úhrade")),
            parse_date(r.get("Dátum splatnosti")),
            parse_float(r.get("Zostáva uhradiť")),
            parse_int(r.get("Dní po splatnosti")),
            parse_date(r.get("Dátum úhrady")),
        ))
    conn.commit()
    print(f"  {len(rows)} invoices imported")

    # Customers
    print("Importing customers...")
    rows = read_csv("/tmp/adresy.csv")
    for r in rows:
        c.execute("""INSERT OR REPLACE INTO zakaznici (
            id, customer_name, customer_street, customer_zipcode,
            customer_city, customer_email, customer_phone
        ) VALUES (?,?,?,?,?,?,?)""", (
            parse_int(r.get("ID")),
            r.get("customer_name", ""),
            r.get("customer_street", ""),
            r.get("customer_zipcode", ""),
            r.get("customer_city", ""),
            r.get("customer_email", ""),
            r.get("customer_phone", ""),
        ))
    conn.commit()
    print(f"  {len(rows)} customers imported")

    # Credits
    print("Importing bank credits...")
    rows = read_csv("/tmp/kredity.csv")
    for r in rows:
        c.execute("""INSERT OR REPLACE INTO kredity (
            id, bankid, acctid, iban, dtstart, dtend, trntype, dtposted,
            dtavail, trnamt, trnvasym, trncosym, reference_e2e, name,
            bankid2, acctid3, iban4, acctkey, memo, currency, trnspsym, poznamka
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            parse_int(r.get("ID")),
            parse_float(r.get("BANKID")),
            parse_float(r.get("ACCTID")),
            r.get("IBAN", ""),
            parse_float(r.get("DTSTART")),
            parse_float(r.get("DTEND")),
            r.get("TRNTYPE", ""),
            parse_float(r.get("DTPOSTED")),
            r.get("DTAVAIL", ""),
            parse_float(r.get("TRNAMT")),
            r.get("TRNVASYM", ""),
            parse_float(r.get("TRNCOSYM")),
            r.get("REFERENCE_E2E", ""),
            r.get("NAME", ""),
            parse_float(r.get("BANKID2")),
            r.get("ACCTID3", ""),
            r.get("IBAN4", ""),
            r.get("ACCTKEY", ""),
            r.get("MEMO", ""),
            r.get("CURRENCY", ""),
            r.get("TRNSPSYM", ""),
            r.get("Poznamka", ""),
        ))
    conn.commit()
    print(f"  {len(rows)} credits imported")

    # Imposition
    print("Importing imposition data...")
    rows = read_csv("/tmp/vyradovanie.csv")
    for r in rows:
        c.execute("""INSERT OR REPLACE INTO vyradovanie (
            id, format, vazba_typ, naklad, stran,
            vn_jph, vn_cph, vn_jpk_cb_na_cb, vn_jpk_far, vn_jpk_far_znizeny,
            vn_jpk_cb_na_far, vn_cpk_cb_na_cb, vn_cpk_far, vn_cpk_cb_na_far, vn_cpk,
            strany_far_v_dok_pocet, far_strany_v_dokumente, cb_strany_v_dokumente,
            pdftk_cb_tlac, pdftk_vkladacky, pdftk_komplet, pdftk_komplet_kratky,
            pdftk_cb_na_far, pdftk_far_na_far,
            cb_strany_pocet, cb_strany, far_strany_pocet, na_far_pocet, klk_na_cb,
            ako_vkladat, cb_klikov_na_far_spolu, pocet_sad, klikov_na_far_spolu,
            far_klikov, pocet_stran_far, na_far, retazec_specifikacie, shuffle_string,
            pocet_stran_vts, pocet_stran_do_shuffle, produkcii, produkcii_vstup,
            bookletova_tlac, far_strany_vts, cb_strany_vts, pocet_cb_stran_vts,
            modulo, statistika, rozsah_stran_vts, oznacenie_zloziek_v_indd,
            rozpis_stran_v_zlozkach, strany_od_do, test1, test2, test3,
            strany_na_th, vn_kliky_spolu_v, typ_vyradenia
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            parse_int(r.get("kalkulacia_ID")),
            r.get("format", ""),
            r.get("vazba_typ", ""),
            parse_int(r.get("naklad")),
            parse_int(r.get("stran")),
            parse_float(r.get("vn_JPH")),
            parse_float(r.get("vn_CPH")),
            parse_float(r.get("vn_JPK_CBnaCB")),
            parse_float(r.get("vn_JPK_FAR")),
            parse_float(r.get("vn_JPK_far_znizeny")),
            parse_float(r.get("vn_JPK_CBnaFAR")),
            parse_int(r.get("vn_CPK_CBnaCB")),
            parse_int(r.get("vn_CPK_FAR")),
            r.get("vn_CPK_CBnaFAR", ""),
            parse_int(r.get("vn_CPK")),
            r.get("StranyFARvDokPocet", ""),
            r.get("FARstranyvDokumente", ""),
            r.get("CBstranyvDokumente", ""),
            r.get("PDFTKstringCBtlac", ""),
            r.get("PDFTKstringVkladacky", ""),
            r.get("PDFTKstringKomplet", ""),
            r.get("PDFTKstringKompletKratky", ""),
            r.get("PDFTKstringCBnaFAR", ""),
            r.get("PDFTKstringFARnaFAR", ""),
            r.get("CBstranyPocet", ""),
            r.get("CBstrany", ""),
            r.get("FARstranyPocet", ""),
            r.get("NaFARPocet", ""),
            r.get("klkNaCB", ""),
            r.get("AkoVkladat", ""),
            parse_int(r.get("CBKlikovNaFARSpolu")),
            parse_int(r.get("PocetSad")),
            parse_int(r.get("KlikovNaFARSpolu")),
            parse_int(r.get("FARKlikov")),
            parse_int(r.get("PocetStranFAR")),
            r.get("NaFAR", ""),
            r.get("RetazecSpecifikacie", ""),
            r.get("ShuffleString", ""),
            parse_int(r.get("PocetStranVTS")),
            parse_int(r.get("PocetStranDoShuffle")),
            parse_int(r.get("produkcii")),
            r.get("ProdukciiVstup", ""),
            parse_bool(r.get("BookletovaTlac")),
            r.get("FARstranyvTS", ""),
            r.get("CBstranyvTS", ""),
            parse_int(r.get("PocetCBstranvTS")),
            parse_float(r.get("modulo")),
            r.get("Statistika", ""),
            r.get("RozsahStranVTS", ""),
            r.get("OznacenieZloziekvIndd", ""),
            r.get("RozpisStranVZlozkach", ""),
            r.get("StranyOdDo", ""),
            r.get("Test1", ""),
            r.get("Test2", ""),
            r.get("Test3", ""),
            r.get("StranyNaTH", ""),
            parse_float(r.get("vn_kliky_spolu_V")),
            r.get("TypVyradenia", ""),
        ))
    conn.commit()
    print(f"  {len(rows)} imposition records imported")

    # Lookup tables
    print("Importing lookup tables...")
    for path, table, cols, keys in [
        ("/tmp/stavy.csv", "stav_projektov", ["id", "nazov"], ["Identifikácia", "Filter projektu"]),
        ("/tmp/status_polozky.csv", "status_polozky", ["id", "nazov"], ["Identifikácia", "Status polozky"]),
        ("/tmp/typ_zakazky.csv", "typ_zakazky", ["id", "nazov"], ["Identifikácia", "Typ zákazky"]),
        ("/tmp/povrch.csv", "povrchova_uprava", ["id", "nazov", "skratka"], ["Identifikácia", "PovrchovaUprava", "PovrchovaUpravaSkratka"]),
        ("/tmp/users.csv", "users", ["id", "username", "plne_meno", "aktualny_projekt", "vynutit_stav", "verzia_db"],
         ["Identifikácia", "User", "PlneMeno", "AktualnyProjekt", "VynutitStav", "VerziaDB"]),
        ("/tmp/podfilter.csv", "podfilter_projektov", ["id", "nazov"], ["Identifikácia", "PodfilterProjektu"]),
        ("/tmp/typ_odmeny.csv", "typ_odmeny", ["id", "nazov"], ["ID typ nákladov", "Typ odmeny"]),
    ]:
        rows = read_csv(path)
        for r in rows:
            vals = []
            for k in keys:
                v = r.get(k, "")
                if k in ("Identifikácia", "ID typ nákladov", "AktualnyProjekt"):
                    v = parse_int(v)
                elif k == "VynutitStav":
                    v = parse_bool(v)
                vals.append(v)
            placeholders = ",".join(["?"] * len(cols))
            col_str = ",".join(cols)
            c.execute(f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})", vals)
        conn.commit()
        print(f"  {table}: {len(rows)} rows")

    # DPH
    rows = read_csv("/tmp/dph.csv")
    for r in rows:
        c.execute("INSERT OR REPLACE INTO sadzba_dph (id, sadzba) VALUES (?,?)", (
            parse_int(r.get("ID sadzba DPH")),
            parse_float(r.get("Sadzba DPH")),
        ))
    conn.commit()
    print(f"  sadzba_dph: {len(rows)} rows")

    # Vazby
    rows = read_csv("/tmp/vazby.csv")
    for r in rows:
        c.execute("INSERT OR REPLACE INTO vazby (id, vazba, popis) VALUES (?,?,?)", (
            parse_int(r.get("Identifikácia")),
            r.get("Vazba", ""),
            r.get("VazbaPopis", ""),
        ))
    conn.commit()
    print(f"  vazby: {len(rows)} rows")

    conn.close()
    print("\nImport complete.")


if __name__ == "__main__":
    run()
