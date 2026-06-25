from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import IQKProdukt, IQKSklad, IQKTransakcia

router = APIRouter(prefix="/api/iqk", tags=["iqk"])


@router.get("/produkty")
async def list_produkty(search: str = "", limit: int = 200, db: AsyncSession = Depends(get_db)):
    q = select(IQKProdukt)
    if search:
        q = q.where(
            IQKProdukt.nazov.ilike(f"%{search}%") |
            IQKProdukt.isbn.ilike(f"%{search}%") |
            IQKProdukt.autor.ilike(f"%{search}%")
        )
    q = q.limit(limit)
    r = await db.execute(q)
    return r.scalars().all()


@router.post("/produkty")
async def create_produkt(data: dict, db: AsyncSession = Depends(get_db)):
    obj = IQKProdukt(**{k: v for k, v in data.items() if hasattr(IQKProdukt, k)})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.get("/produkty/{pid}")
async def get_produkt(pid: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IQKProdukt).where(IQKProdukt.id == pid))
    return r.scalar_one_or_none()


@router.put("/produkty/{pid}")
async def update_produkt(pid: int, data: dict, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IQKProdukt).where(IQKProdukt.id == pid))
    obj = r.scalar_one_or_none()
    if not obj:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/produkty/{pid}")
async def delete_produkt(pid: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IQKProdukt).where(IQKProdukt.id == pid))
    obj = r.scalar_one_or_none()
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


@router.get("/produkty/{pid}/transakcie")
async def list_transakcie(pid: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IQKTransakcia).where(IQKTransakcia.produkt_id == pid).order_by(IQKTransakcia.datum.desc()))
    return r.scalars().all()


@router.post("/transakcie")
async def create_transakcia(data: dict, db: AsyncSession = Depends(get_db)):
    obj = IQKTransakcia(**{k: v for k, v in data.items() if hasattr(IQKTransakcia, k)})
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.put("/transakcie/{tid}")
async def update_transakcia(tid: int, data: dict, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IQKTransakcia).where(IQKTransakcia.id == tid))
    obj = r.scalar_one_or_none()
    if not obj:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/transakcie/{tid}")
async def delete_transakcia(tid: int, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(IQKTransakcia).where(IQKTransakcia.id == tid))
    obj = r.scalar_one_or_none()
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


@router.get("/statistika")
async def statistika(db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(IQKProdukt.id)))).scalar() or 0
    transakcie = (await db.execute(select(func.count(IQKTransakcia.id)))).scalar() or 0
    suma = (await db.execute(select(func.sum(IQKTransakcia.suma)))).scalar() or 0
    return {"produktov": total, "transakcii": transakcie, "suma_celkom": suma}
