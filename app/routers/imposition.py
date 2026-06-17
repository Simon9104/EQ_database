from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import Imposition

router = APIRouter(prefix="/api/imposition", tags=["imposition"])


@router.get("")
async def list_imposition(
    format: Optional[str] = None,
    vazba_typ: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(Imposition)
    if format:
        q = q.where(Imposition.format == format)
    if vazba_typ:
        q = q.where(Imposition.vazba_typ == vazba_typ)
    q = q.order_by(Imposition.id.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{imp_id}")
async def get_imposition(imp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Imposition).where(Imposition.id == imp_id))
    return result.scalar_one_or_none()


@router.post("")
async def create_imposition(data: dict, db: AsyncSession = Depends(get_db)):
    imp = Imposition(**data)
    db.add(imp)
    await db.commit()
    await db.refresh(imp)
    return imp


@router.put("/{imp_id}")
async def update_imposition(imp_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Imposition).where(Imposition.id == imp_id))
    imp = result.scalar_one_or_none()
    if not imp:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(imp, k):
            setattr(imp, k, v)
    await db.commit()
    await db.refresh(imp)
    return imp


@router.delete("/{imp_id}")
async def delete_imposition(imp_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Imposition).where(Imposition.id == imp_id))
    imp = result.scalar_one_or_none()
    if imp:
        await db.delete(imp)
        await db.commit()
    return {"ok": True}
