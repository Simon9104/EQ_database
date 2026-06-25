from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import init_db, get_db
from app.models import Project, Invoice, Customer
from app.routers import projects, items, invoices, customers, credits, imposition, lookups
from app.routers import firmy, kontakty, naklady, iqk, bank, auth
from app.database import AsyncSessionLocal
import csv, io


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await auth.ensure_default_admin(db)
    yield


app = FastAPI(title="EQ Projekty", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(items.router)
app.include_router(invoices.router)
app.include_router(customers.router)
app.include_router(credits.router)
app.include_router(imposition.router)
app.include_router(lookups.router)
app.include_router(lookups.stavy_router)
app.include_router(lookups.status_polozky_router)
app.include_router(lookups.typ_zakazky_router)
app.include_router(lookups.vazby_router)
app.include_router(lookups.povrch_router)
app.include_router(lookups.dph_router)
app.include_router(lookups.users_router)
app.include_router(lookups.podfilter_router)
app.include_router(lookups.odmeny_router)
app.include_router(lookups.typ_nakladov_router)
app.include_router(lookups.obalka_ceny_router)
app.include_router(firmy.router)
app.include_router(kontakty.router)
app.include_router(naklady.router)
app.include_router(iqk.router)
app.include_router(bank.router)
app.include_router(auth.router)
app.include_router(lookups.jazyky_iqk_router)
app.include_router(lookups.hviezdicky_router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    proj_total = (await db.execute(select(func.count()).select_from(Project))).scalar()
    proj_by_stav = (await db.execute(
        select(Project.stav, func.count()).group_by(Project.stav)
    )).all()

    inv_result = await db.execute(select(
        func.count(),
        func.sum(Invoice.suma_s_dph),
        func.sum(Invoice.zostava_uhradit)
    ).select_from(Invoice))
    inv_count, inv_total, inv_zostava = inv_result.one()

    overdue = (await db.execute(
        select(func.count()).where(Invoice.dni_po_splatnosti > 0).where(Invoice.zostava_uhradit > 0)
    )).scalar()

    return {
        "projekty_celkom": proj_total,
        "projekty_podla_stavu": [{"stav": r[0] or "—", "pocet": r[1]} for r in proj_by_stav],
        "faktury_celkom": inv_count,
        "faktury_suma": float(inv_total or 0),
        "faktury_zostava": float(inv_zostava or 0),
        "faktury_po_splatnosti": overdue,
    }


@app.get("/api/export/projects")
async def export_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.id.desc()))
    projects_list = result.scalars().all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID", "Projekt", "Firma", "Manažér", "Stav", "Prijaté", "Termín", "Cena s DPH", "Zisk"])
    for p in projects_list:
        w.writerow([p.id, p.nazov_projektu, p.nazov_firmy, p.manazer, p.stav,
                    p.prijate, p.termin_odovzdania, p.cena_s_dph, p.zisk])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=projekty.csv"})


@app.get("/api/export/invoices")
async def export_invoices(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).order_by(Invoice.datum_vystavenia.desc()))
    invs = result.scalars().all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["Č. FA", "Dátum", "Odberateľ", "Popis", "Bez DPH", "s DPH", "k úhrade",
                "Splatnosť", "Zostáva", "Dní po spl.", "Dátum úhrady"])
    for f in invs:
        w.writerow([f.cislo_faktury, f.datum_vystavenia, f.odberatel, f.popis,
                    f.suma_bez_dph, f.suma_s_dph, f.suma_k_uhrade,
                    f.datum_splatnosti, f.zostava_uhradit, f.dni_po_splatnosti, f.datum_uhrady])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=faktury.csv"})


@app.get("/login")
async def login_page():
    return FileResponse("static/login.html")


@app.get("/")
async def root(request: Request):
    token = request.cookies.get("eq_token")
    if not token or not auth.decode_token(token):
        return RedirectResponse("/login")
    return FileResponse("static/index.html")
