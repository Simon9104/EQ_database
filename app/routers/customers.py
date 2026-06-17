from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import Customer

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
async def list_customers(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(Customer)
    if search:
        q = q.where(Customer.customer_name.ilike(f"%{search}%"))
    q = q.order_by(Customer.customer_name).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{customer_id}")
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    return result.scalar_one_or_none()


@router.post("")
async def create_customer(data: dict, db: AsyncSession = Depends(get_db)):
    c = Customer(**data)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@router.put("/{customer_id}")
async def update_customer(customer_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    c = result.scalar_one_or_none()
    if not c:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(c, k):
            setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return c


@router.delete("/{customer_id}")
async def delete_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    c = result.scalar_one_or_none()
    if c:
        await db.delete(c)
        await db.commit()
    return {"ok": True}
