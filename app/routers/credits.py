from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import Credit

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("")
async def list_credits(
    search: Optional[str] = None,
    trntype: Optional[str] = None,
    skip: int = 0,
    limit: int = 300,
    db: AsyncSession = Depends(get_db),
):
    q = select(Credit)
    if search:
        q = q.where(Credit.name.ilike(f"%{search}%"))
    if trntype:
        q = q.where(Credit.trntype == trntype)
    q = q.order_by(Credit.dtposted.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{credit_id}")
async def get_credit(credit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Credit).where(Credit.id == credit_id))
    return result.scalar_one_or_none()


@router.post("")
async def create_credit(data: dict, db: AsyncSession = Depends(get_db)):
    c = Credit(**data)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.put("/{credit_id}")
async def update_credit(credit_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Credit).where(Credit.id == credit_id))
    c = result.scalar_one_or_none()
    if not c:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(c, k):
            setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/{credit_id}")
async def delete_credit(credit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Credit).where(Credit.id == credit_id))
    c = result.scalar_one_or_none()
    if c:
        await db.delete(c)
        await db.commit()
    return {"ok": True}
