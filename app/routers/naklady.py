from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Naklad

router = APIRouter(tags=["naklady"])


@router.get("/api/projects/{project_id}/naklady")
async def list_naklady(project_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Naklad).where(Naklad.id_projektu == project_id).order_by(Naklad.id))
    return r.scalars().all()


@router.post("/api/projects/{project_id}/naklady")
async def create_naklad(project_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    data["id_projektu"] = project_id
    obj = Naklad(**{k: v for k, v in data.items() if hasattr(Naklad, k)})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.put("/api/naklady/{naklad_id}")
async def update_naklad(naklad_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Naklad).where(Naklad.id == naklad_id))
    obj = r.scalar_one_or_none()
    if not obj:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/api/naklady/{naklad_id}")
async def delete_naklad(naklad_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Naklad).where(Naklad.id == naklad_id))
    obj = r.scalar_one_or_none()
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}
