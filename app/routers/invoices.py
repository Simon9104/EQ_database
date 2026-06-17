from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import Invoice

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("")
async def list_invoices(
    search: Optional[str] = None,
    nezaplatene: Optional[bool] = None,
    po_splatnosti: Optional[bool] = None,
    skip: int = 0,
    limit: int = 300,
    db: AsyncSession = Depends(get_db),
):
    q = select(Invoice)
    if search:
        q = q.where(Invoice.odberatel.ilike(f"%{search}%"))
    if nezaplatene:
        q = q.where(Invoice.zostava_uhradit > 0)
    if po_splatnosti:
        q = q.where(Invoice.dni_po_splatnosti > 0)
    q = q.order_by(Invoice.datum_vystavenia.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    return result.scalar_one_or_none()


@router.post("")
async def create_invoice(data: dict, db: AsyncSession = Depends(get_db)):
    inv = Invoice(**data)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.put("/{invoice_id}")
async def update_invoice(invoice_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(inv, k):
            setattr(inv, k, v)
    await db.commit()
    await db.refresh(inv)
    return inv


@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if inv:
        await db.delete(inv)
        await db.commit()
    return {"ok": True}
