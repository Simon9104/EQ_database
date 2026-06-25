from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import (
    StavProjektu, StatusPolozky, TypZakazky, Vazba,
    PovrchovaUprava, SadzbaDPH, User, PodfilterProjektu, TypOdmeny,
    TypNakladu, ObalkaCena
)

router = APIRouter(prefix="/api/lookups", tags=["lookups"])


@router.get("")
async def get_all_lookups(db: AsyncSession = Depends(get_db)):
    async def fetch(model):
        r = await db.execute(select(model))
        rows = r.scalars().all()
        return [row.__dict__ for row in rows]

    return {
        "stavy_projektov": await fetch(StavProjektu),
        "status_polozky": await fetch(StatusPolozky),
        "typy_zakaziek": await fetch(TypZakazky),
        "vazby": await fetch(Vazba),
        "povrchova_uprava": await fetch(PovrchovaUprava),
        "sadzby_dph": await fetch(SadzbaDPH),
        "users": await fetch(User),
        "podfilter_projektov": await fetch(PodfilterProjektu),
        "typy_odmeny": await fetch(TypOdmeny),
        "typy_nakladov": await fetch(TypNakladu),
        "obalka_ceny": await fetch(ObalkaCena),
    }


def make_crud(model, prefix):
    sub = APIRouter(prefix=f"/api/{prefix}", tags=[prefix])

    @sub.get("")
    async def lst(db: AsyncSession = Depends(get_db)):
        r = await db.execute(select(model))
        return r.scalars().all()

    @sub.post("")
    async def create(data: dict, db: AsyncSession = Depends(get_db)):
        obj = model(**data)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @sub.put("/{obj_id}")
    async def update(obj_id: int, data: dict, db: AsyncSession = Depends(get_db)):
        r = await db.execute(select(model).where(model.id == obj_id))
        obj = r.scalar_one_or_none()
        if not obj:
            return {"error": "not found"}
        for k, v in data.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        await db.commit()
        await db.refresh(obj)
        return obj

    @sub.delete("/{obj_id}")
    async def delete(obj_id: int, db: AsyncSession = Depends(get_db)):
        r = await db.execute(select(model).where(model.id == obj_id))
        obj = r.scalar_one_or_none()
        if obj:
            await db.delete(obj)
            await db.commit()
        return {"ok": True}

    return sub


typ_nakladov_router = make_crud(TypNakladu, "typy-nakladov")
obalka_ceny_router = make_crud(ObalkaCena, "obalka-ceny")
stavy_router = make_crud(StavProjektu, "stavy")
status_polozky_router = make_crud(StatusPolozky, "status-polozky")
typ_zakazky_router = make_crud(TypZakazky, "typy-zakaziek")
vazby_router = make_crud(Vazba, "vazby")
povrch_router = make_crud(PovrchovaUprava, "povrchova-uprava")
dph_router = make_crud(SadzbaDPH, "sadzby-dph")
users_router = make_crud(User, "users")
podfilter_router = make_crud(PodfilterProjektu, "podfilter")
odmeny_router = make_crud(TypOdmeny, "typy-odmeny")
