from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Kontakt

router = APIRouter(prefix="/api/kontakty", tags=["kontakty"])


@router.get("")
async def list_kontakty(
    firma_id: int = Query(None),
    search: str = Query(None),
    limit: int = Query(200),
    db: AsyncSession = Depends(get_db),
):
    q = select(Kontakt)
    if firma_id:
        q = q.where(Kontakt.firma_id == firma_id)
    if search:
        q = q.where(
            Kontakt.priezvisko.ilike(f"%{search}%") |
            Kontakt.meno.ilike(f"%{search}%") |
            Kontakt.email.ilike(f"%{search}%")
        )
    q = q.order_by(Kontakt.priezvisko).limit(limit)
    r = await db.execute(q)
    return r.scalars().all()


@router.post("")
async def create_kontakt(data: dict, db: AsyncSession = Depends(get_db)):
    obj = Kontakt(**{k: v for k, v in data.items() if hasattr(Kontakt, k)})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{kontakt_id}")
async def get_kontakt(kontakt_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Kontakt).where(Kontakt.id == kontakt_id))
    return r.scalar_one_or_none()


@router.put("/{kontakt_id}")
async def update_kontakt(kontakt_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Kontakt).where(Kontakt.id == kontakt_id))
    obj = r.scalar_one_or_none()
    if not obj:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{kontakt_id}")
async def delete_kontakt(kontakt_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Kontakt).where(Kontakt.id == kontakt_id))
    obj = r.scalar_one_or_none()
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}
