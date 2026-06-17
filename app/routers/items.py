from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models import Item

router = APIRouter(tags=["items"])


@router.get("/api/projects/{project_id}/items")
async def list_items(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Item).where(Item.id_projektu == project_id).order_by(Item.poradie)
    )
    return result.scalars().all()


@router.post("/api/projects/{project_id}/items")
async def create_item(project_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    data["id_projektu"] = project_id
    item = Item(**data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/api/items")
async def list_all_items(
    status: Optional[str] = None,
    typ_zakazky: Optional[str] = None,
    fakturovat: Optional[bool] = None,
    fakturovane: Optional[bool] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(Item)
    if status:
        q = q.where(Item.status == status)
    if typ_zakazky:
        q = q.where(Item.typ_zakazky == typ_zakazky)
    if fakturovat is not None:
        q = q.where(Item.fakturovat == fakturovat)
    if fakturovane is not None:
        q = q.where(Item.fakturovane == fakturovane)
    q = q.order_by(Item.id.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.put("/api/items/{item_id}")
async def update_item(item_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(item, k):
            setattr(item, k, v)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/api/items/{item_id}")
async def delete_item(item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.commit()
    return {"ok": True}
