from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import FiremneUdaje
from app.routers.auth import get_admin_user

router = APIRouter(prefix="/api/firemne-udaje", tags=["firemne-udaje"])


@router.get("")
async def get_firemne_udaje(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FiremneUdaje).where(FiremneUdaje.id == 1))
    ud = result.scalar_one_or_none()
    if not ud:
        return {}
    return ud


@router.put("")
async def update_firemne_udaje(
    data: dict,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(get_admin_user),
):
    result = await db.execute(select(FiremneUdaje).where(FiremneUdaje.id == 1))
    ud = result.scalar_one_or_none()
    allowed = {c.key for c in FiremneUdaje.__table__.columns} - {"id"}
    if not ud:
        ud = FiremneUdaje(id=1, **{k: v for k, v in data.items() if k in allowed})
        db.add(ud)
    else:
        for k, v in data.items():
            if k in allowed:
                setattr(ud, k, v)
    await db.commit()
    if ud.id:
        await db.refresh(ud)
    return ud
