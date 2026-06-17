from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, BigInteger
from app.database import Base


class Project(Base):
    __tablename__ = "projekty"
    id = Column(Integer, primary_key=True, index=True)
    nazov_projektu = Column(Text)
    nazov_firmy = Column(String(255))
    priezvisko_meno = Column(String(255))
    manazer = Column(String(255))
    kategoria = Column(String(50))
    priorita = Column(String(50))
    stav = Column(String(50))
    f1 = Column(String(50))
    f2 = Column(String(50))
    f3 = Column(String(50))
    f4 = Column(String(20))
    stav2 = Column(String(50))
    stav3 = Column(String(50))
    force = Column(Boolean, default=False)
    prijate = Column(DateTime)
    prijal = Column(String(255))
    termin_odovzdania = Column(DateTime)
    zostava = Column(String(255))
    poznamky = Column(Text)
    poznamky_zl = Column(Text)
    poznamky_1 = Column(Text)
    poznamka_cp = Column(Text)
    folder_zakazky = Column(String(255))
    folder_cp = Column(String(255))
    cislo_objednavky = Column(String(255))
    datum_prijatia_objednavky = Column(DateTime)
    datum_na_objednavke = Column(DateTime)
    cena_bez_dph = Column(Float, default=0)
    dph_ceny = Column(Float, default=0)
    cena_s_dph = Column(Float, default=0)
    naklady = Column(Float, default=0)
    zisk = Column(Float, default=0)
    cena_bez_fa = Column(Float, default=0)
    naklady_bez_fa = Column(Float, default=0)
    vpt_agenturnacena = Column(Boolean, default=False)
    projekt_expedovat = Column(Boolean, default=False)
    projekt_expedovat_datum = Column(DateTime)
    projekt_oznaceny = Column(Boolean, default=False)
    projekt_kreditny = Column(Boolean, default=False)
    projekt_zberny = Column(Boolean, default=False)
    projekt_fakturovany = Column(Boolean, default=False)
    projekt_fakturovany_vopred = Column(Boolean, default=False)
    projekt_uhradeny = Column(Boolean, default=False)
    projekt_cp = Column(Boolean, default=False)
    projekt_sledovany = Column(Boolean, default=False)
    projekt_kniha = Column(Boolean, default=False)
    projekt_cakajuci = Column(Boolean, default=False)
    projekt_bezny = Column(Boolean, default=False)
    projekt_hotovo = Column(Boolean, default=False)
    kredit = Column(Float, default=0)
    zucastneni = Column(String(255))
    strucna_specifikacia = Column(String(255))
    cislo_cp = Column(String(50))
    podobny_projekt = Column(String(255))
    projekt_log = Column(Text)


class Item(Base):
    __tablename__ = "polozky"
    id = Column(Integer, primary_key=True, index=True)
    poradie = Column(Integer)
    id_projektu = Column(Integer, index=True)
    popis = Column(String(255))
    podpopis = Column(Text)
    strucna_specifikacia = Column(String(255))
    mj = Column(String(20))
    pocet = Column(Float, default=0)
    jc = Column(Float, default=0)
    cena = Column(Float, default=0)
    zlava = Column(Float, default=0)
    sadzba_dph = Column(Float, default=0)
    cena_s_dph = Column(Float, default=0)
    status = Column(String(20))
    typ_zakazky = Column(String(20))
    polozka_pracuje = Column(String(20))
    fakturovat = Column(Boolean, default=False)
    fakturovane = Column(Boolean, default=False)
    faktura_vopred = Column(Boolean, default=False)
    do_faktury = Column(Boolean, default=False)
    kto_fakturuje = Column(String(20))
    datum_fakturacie = Column(DateTime)
    cislo_faktury = Column(String(20))
    id_faktury = Column(String(255))
    poznamka = Column(Text)
    poznamka_vl = Column(Text)
    vyber_x = Column(Boolean, default=False)
    polozka_x = Column(Boolean, default=False)
    dl = Column(Boolean, default=False)
    objednavka_x = Column(Boolean, default=False)
    cp_polozky_x = Column(Boolean, default=False)
    odovzdane = Column(Boolean, default=False)
    typ_kalkulacie = Column(String(30))
    pocet_stran = Column(Integer)
    pocet_stran_far = Column(Integer)
    format = Column(String(255))
    vazba = Column(String(255))
    db_vn_papier_typ = Column(String(30))
    db_vn_papier_lesk_mat = Column(String(255))
    db_vn_papier_specifikacia = Column(String(255))
    db_ob_farebnost = Column(String(30))
    db_ob_papier_typ = Column(String(30))
    db_ob_papier_lesk_mat = Column(String(255))
    db_ob_pu = Column(String(30))
    db_ob_pu_skratka = Column(String(30))
    db_chrbat = Column(String(255))
    db_lacetka = Column(String(255))
    format_th = Column(String(10))
    far_strany = Column(Text)
    cb_klikov_na_far_spolu = Column(Integer)
    pocet_sad = Column(Integer)
    klikov_na_far_spolu = Column(Integer)
    far_klikov = Column(Integer)
    vkladacky_ano_nie = Column(Boolean, default=False)
    vkladacky_text = Column(Text)
    pocet_th_obalky = Column(String(255))
    ako_vkladat = Column(Text)
    na_far = Column(Text)
    pdftk_cb_tlac = Column(String(255))
    pdftk_vkladacky = Column(String(255))
    pdftk_komplet = Column(Text)
    pdftk_komplet_kratky = Column(Text)
    cb_strany_pocet = Column(String(255))
    cb_strany = Column(Text)
    cb_na_cb_pocet = Column(String(255))
    cb_na_far_pocet = Column(String(255))
    na_cb_pocet = Column(String(255))
    far_strany_pocet = Column(String(255))
    na_far_pocet = Column(String(255))
    klk_na_cb = Column(String(255))
    polozka_expedovat = Column(Boolean, default=False)
    polozka_expedovat_datum = Column(DateTime)
    komu_dodat = Column(String(255))
    polozka_kde_vyzdvihnut = Column(String(255))
    filter_vazba_retazec = Column(String(255))
    zhrnuty_text_vyradovaca = Column(Text)
    id_produktu_db = Column(Integer)


class Invoice(Base):
    __tablename__ = "faktury"
    id = Column(Integer, primary_key=True, index=True)
    cislo_faktury = Column(String(255), index=True)
    datum_vystavenia = Column(DateTime)
    odberatel = Column(String(255))
    popis = Column(String(255))
    suma_bez_dph = Column(Float, default=0)
    suma_s_dph = Column(Float, default=0)
    suma_k_uhrade = Column(Float, default=0)
    datum_splatnosti = Column(DateTime)
    zostava_uhradit = Column(Float, default=0)
    dni_po_splatnosti = Column(Integer)
    datum_uhrady = Column(DateTime)


class Customer(Base):
    __tablename__ = "zakaznici"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(255))
    customer_street = Column(Text)
    customer_zipcode = Column(String(255))
    customer_city = Column(String(255))
    customer_email = Column(String(255))
    customer_phone = Column(String(255))


class Credit(Base):
    __tablename__ = "kredity"
    id = Column(Integer, primary_key=True, index=True)
    bankid = Column(Float)
    acctid = Column(Float)
    iban = Column(String(255))
    dtstart = Column(Float)
    dtend = Column(Float)
    trntype = Column(String(255))
    dtposted = Column(Float)
    dtavail = Column(String(255))
    trnamt = Column(Float, default=0)
    trnvasym = Column(String(255))
    trncosym = Column(Float)
    reference_e2e = Column(String(255))
    name = Column(String(255))
    bankid2 = Column(Float)
    acctid3 = Column(String(255))
    iban4 = Column(String(255))
    acctkey = Column(String(255))
    memo = Column(String(255))
    currency = Column(String(255))
    trnspsym = Column(String(255))
    poznamka = Column(String(255))


class Imposition(Base):
    __tablename__ = "vyradovanie"
    id = Column(Integer, primary_key=True, index=True)
    format = Column(String(30))
    vazba_typ = Column(String(255))
    naklad = Column(Integer)
    stran = Column(Integer)
    vn_jph = Column(Float)
    vn_cph = Column(Float)
    vn_jpk_cb_na_cb = Column(Float)
    vn_jpk_far = Column(Float)
    vn_jpk_far_znizeny = Column(Float)
    vn_jpk_cb_na_far = Column(Float)
    vn_cpk_cb_na_cb = Column(Integer)
    vn_cpk_far = Column(Integer)
    vn_cpk_cb_na_far = Column(String(255))
    vn_cpk = Column(Integer)
    strany_far_v_dok_pocet = Column(Text)
    far_strany_v_dokumente = Column(Text)
    cb_strany_v_dokumente = Column(Text)
    pdftk_cb_tlac = Column(Text)
    pdftk_vkladacky = Column(Text)
    pdftk_komplet = Column(Text)
    pdftk_komplet_kratky = Column(Text)
    pdftk_cb_na_far = Column(Text)
    pdftk_far_na_far = Column(Text)
    cb_strany_pocet = Column(String(255))
    cb_strany = Column(Text)
    far_strany_pocet = Column(String(255))
    na_far_pocet = Column(String(255))
    klk_na_cb = Column(String(255))
    ako_vkladat = Column(Text)
    cb_klikov_na_far_spolu = Column(Integer)
    pocet_sad = Column(Integer)
    klikov_na_far_spolu = Column(Integer)
    far_klikov = Column(Integer)
    pocet_stran_far = Column(Integer)
    na_far = Column(Text)
    retazec_specifikacie = Column(String(255))
    shuffle_string = Column(Text)
    pocet_stran_vts = Column(Integer)
    pocet_stran_do_shuffle = Column(Integer)
    produkcii = Column(Integer)
    produkcii_vstup = Column(String(255))
    bookletova_tlac = Column(Boolean, default=False)
    far_strany_vts = Column(Text)
    cb_strany_vts = Column(Text)
    pocet_cb_stran_vts = Column(Integer)
    modulo = Column(Float)
    statistika = Column(Text)
    rozsah_stran_vts = Column(Text)
    oznacenie_zloziek_v_indd = Column(Text)
    rozpis_stran_v_zlozkach = Column(Text)
    strany_od_do = Column(Text)
    test1 = Column(Text)
    test2 = Column(Text)
    test3 = Column(Text)
    strany_na_th = Column(Text)
    vn_kliky_spolu_v = Column(Float)
    typ_vyradenia = Column(Text)


# Lookup tables
class StavProjektu(Base):
    __tablename__ = "stav_projektov"
    id = Column(Integer, primary_key=True)
    nazov = Column(String(255))


class StatusPolozky(Base):
    __tablename__ = "status_polozky"
    id = Column(Integer, primary_key=True)
    nazov = Column(String(255))


class TypZakazky(Base):
    __tablename__ = "typ_zakazky"
    id = Column(Integer, primary_key=True)
    nazov = Column(String(255))


class Vazba(Base):
    __tablename__ = "vazby"
    id = Column(Integer, primary_key=True)
    vazba = Column(String(20))
    popis = Column(String(30))


class PovrchovaUprava(Base):
    __tablename__ = "povrchova_uprava"
    id = Column(Integer, primary_key=True)
    nazov = Column(String(20))
    skratka = Column(String(30))


class SadzbaDPH(Base):
    __tablename__ = "sadzba_dph"
    id = Column(Integer, primary_key=True)
    sadzba = Column(Float)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255))
    plne_meno = Column(String(255))
    aktualny_projekt = Column(Integer)
    vynutit_stav = Column(Boolean, default=False)
    verzia_db = Column(String(255))


class PodfilterProjektu(Base):
    __tablename__ = "podfilter_projektov"
    id = Column(Integer, primary_key=True)
    nazov = Column(String(255))


class TypOdmeny(Base):
    __tablename__ = "typ_odmeny"
    id = Column(Integer, primary_key=True)
    nazov = Column(String(255))
