from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models import Firma, Kontakt

router = APIRouter(prefix="/api/firmy", tags=["firmy"])


@router.get("")
async def list_firmy(
    search: str = Query(None),
    odberatel: bool = Query(None),
    dodavatel: bool = Query(None),
    limit: int = Query(300),
    db: AsyncSession = Depends(get_db),
):
    q = select(Firma)
    if search:
        q = q.where(or_(Firma.nazov.ilike(f"%{search}%"), Firma.email.ilike(f"%{search}%"), Firma.ico.ilike(f"%{search}%")))
    if odberatel is not None:
        q = q.where(Firma.odberatel == odberatel)
    if dodavatel is not None:
        q = q.where(Firma.dodavatel == dodavatel)
    q = q.order_by(Firma.nazov).limit(limit)
    r = await db.execute(q)
    return r.scalars().all()


@router.post("")
async def create_firma(data: dict, db: AsyncSession = Depends(get_db)):
    obj = Firma(**{k: v for k, v in data.items() if hasattr(Firma, k)})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/{firma_id}")
async def get_firma(firma_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Firma).where(Firma.id == firma_id))
    return r.scalar_one_or_none()


@router.put("/{firma_id}")
async def update_firma(firma_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Firma).where(Firma.id == firma_id))
    obj = r.scalar_one_or_none()
    if not obj:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{firma_id}")
async def delete_firma(firma_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Firma).where(Firma.id == firma_id))
    obj = r.scalar_one_or_none()
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


@router.get("/{firma_id}/kontakty")
async def get_firma_kontakty(firma_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Kontakt).where(Kontakt.firma_id == firma_id))
    return r.scalars().all()
