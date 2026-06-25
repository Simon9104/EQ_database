from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, inspect
from app.database import get_db
from app.models import (
    StavProjektu, StatusPolozky, TypZakazky, Vazba,
    PovrchovaUprava, SadzbaDPH, User, PodfilterProjektu, TypOdmeny,
    TypNakladu, ObalkaCena, JazykIQK, Hviezdicky
)
from app.routers.auth import get_admin_user

# Columns that must never be set via API on any model
_BLOCKED_COLUMNS = {"password_hash", "is_admin", "active"}

router = APIRouter(prefix="/api/lookups", tags=["lookups"])

SAFE_USER_FIELDS = {"id", "username", "plne_meno", "aktualny_projekt", "vynutit_stav", "is_admin", "active"}


@router.get("")
async def get_all_lookups(db: AsyncSession = Depends(get_db)):
    async def fetch(model):
        r = await db.execute(select(model))
        rows = r.scalars().all()
        return [row.__dict__ for row in rows]

    async def fetch_users():
        r = await db.execute(select(User))
        rows = r.scalars().all()
        return [{k: v for k, v in row.__dict__.items() if k in SAFE_USER_FIELDS} for row in rows]

    return {
        "stavy_projektov": await fetch(StavProjektu),
        "status_polozky": await fetch(StatusPolozky),
        "typy_zakaziek": await fetch(TypZakazky),
        "vazby": await fetch(Vazba),
        "povrchova_uprava": await fetch(PovrchovaUprava),
        "sadzby_dph": await fetch(SadzbaDPH),
        "users": await fetch_users(),
        "podfilter_projektov": await fetch(PodfilterProjektu),
        "typy_odmeny": await fetch(TypOdmeny),
        "typy_nakladov": await fetch(TypNakladu),
        "obalka_ceny": await fetch(ObalkaCena),
        "jazyky_iqk": await fetch(JazykIQK),
        "hviezdicky": await fetch(Hviezdicky),
    }


def _safe_columns(model):
    """Return the set of column names allowed for create/update via API."""
    try:
        cols = {c.key for c in inspect(model).mapper.column_attrs}
    except Exception:
        cols = set()
    return cols - _BLOCKED_COLUMNS - {"id"}


def make_crud(model, prefix, require_auth=False):
    sub = APIRouter(prefix=f"/api/{prefix}", tags=[prefix])
    auth_dep = [Depends(get_admin_user)] if require_auth else []

    @sub.get("")
    async def lst(db: AsyncSession = Depends(get_db)):
        r = await db.execute(select(model))
        return r.scalars().all()

    @sub.post("", dependencies=auth_dep)
    async def create(data: dict, db: AsyncSession = Depends(get_db)):
        allowed = _safe_columns(model)
        filtered = {k: v for k, v in data.items() if k in allowed}
        obj = model(**filtered)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @sub.put("/{obj_id}", dependencies=auth_dep)
    async def update(obj_id: int, data: dict, db: AsyncSession = Depends(get_db)):
        r = await db.execute(select(model).where(model.id == obj_id))
        obj = r.scalar_one_or_none()
        if not obj:
            return {"error": "not found"}
        allowed = _safe_columns(model)
        for k, v in data.items():
            if k in allowed:
                setattr(obj, k, v)
        await db.commit()
        await db.refresh(obj)
        return obj

    @sub.delete("/{obj_id}", dependencies=auth_dep)
    async def delete(obj_id: int, db: AsyncSession = Depends(get_db)):
        r = await db.execute(select(model).where(model.id == obj_id))
        obj = r.scalar_one_or_none()
        if obj:
            await db.delete(obj)
            await db.commit()
        return {"ok": True}

    return sub


jazyky_iqk_router = make_crud(JazykIQK, "jazyky-iqk", require_auth=True)
hviezdicky_router = make_crud(Hviezdicky, "hviezdicky", require_auth=True)
typ_nakladov_router = make_crud(TypNakladu, "typy-nakladov", require_auth=True)
obalka_ceny_router = make_crud(ObalkaCena, "obalka-ceny", require_auth=True)
stavy_router = make_crud(StavProjektu, "stavy", require_auth=True)
status_polozky_router = make_crud(StatusPolozky, "status-polozky", require_auth=True)
typ_zakazky_router = make_crud(TypZakazky, "typy-zakaziek", require_auth=True)
vazby_router = make_crud(Vazba, "vazby", require_auth=True)
povrch_router = make_crud(PovrchovaUprava, "povrchova-uprava", require_auth=True)
dph_router = make_crud(SadzbaDPH, "sadzby-dph", require_auth=True)
podfilter_router = make_crud(PodfilterProjektu, "podfilter", require_auth=True)
odmeny_router = make_crud(TypOdmeny, "typy-odmeny", require_auth=True)
