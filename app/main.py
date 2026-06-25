from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import init_db, get_db
from app.models import Project, Invoice, Customer
from app.routers import projects, items, invoices, customers, credits, imposition, lookups
from app.routers import firmy, kontakty, naklady, iqk, bank, auth
from app.database import AsyncSessionLocal
import csv, io, time
from collections import defaultdict

# ── Simple in-memory rate limiter for login ───────────────────────────────────
_login_attempts: dict = defaultdict(list)
_LOGIN_WINDOW = 60   # seconds
_LOGIN_MAX = 10      # max attempts per window per IP

def check_rate_limit(ip: str) -> bool:
    now = time.time()
    attempts = _login_attempts[ip]
    _login_attempts[ip] = [t for t in attempts if now - t < _LOGIN_WINDOW]
    if len(_login_attempts[ip]) >= _LOGIN_MAX:
        return False
    _login_attempts[ip].append(now)
    return True


# ── Auth guard middleware: protect all /api/* except /api/auth/* ──────────────
_PUBLIC_PREFIXES = ("/api/auth/login", "/api/auth/logout", "/api/auth/me")

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/"):
            if not any(path.startswith(p) for p in _PUBLIC_PREFIXES):
                token = request.cookies.get("eq_token") or \
                    request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
                if not token or not auth.decode_token(token):
                    return JSONResponse({"detail": "Nie ste prihlásený"}, status_code=401)
        response = await call_next(request)
        # Security headers on every response
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as db:
        await auth.ensure_default_admin(db)
    yield


app = FastAPI(title="EQ Projekty", lifespan=lifespan)

# CORS: restrict to same origin in production (no wildcard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
app.add_middleware(AuthMiddleware)

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
async def dashboard(request: Request, db: AsyncSession = Depends(get_db), _user=Depends(auth.get_current_user)):
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
async def export_projects(db: AsyncSession = Depends(get_db), _user=Depends(auth.get_current_user)):
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
async def export_invoices(db: AsyncSession = Depends(get_db), _user=Depends(auth.get_current_user)):
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
