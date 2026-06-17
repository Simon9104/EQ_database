from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
from app.database import get_db
from app.models import Project

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("")
async def list_projects(
    stav: Optional[str] = None,
    search: Optional[str] = None,
    manazer: Optional[str] = None,
    kreditny: Optional[bool] = None,
    zberny: Optional[bool] = None,
    kniha: Optional[bool] = None,
    cp: Optional[bool] = None,
    oznaceny: Optional[bool] = None,
    cakajuci: Optional[bool] = None,
    bezny: Optional[bool] = None,
    hotovo: Optional[bool] = None,
    expedovat: Optional[bool] = None,
    sledovany: Optional[bool] = None,
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(Project)
    if stav:
        q = q.where(Project.stav == stav)
    if search:
        q = q.where(or_(
            Project.nazov_projektu.ilike(f"%{search}%"),
            Project.nazov_firmy.ilike(f"%{search}%"),
            Project.priezvisko_meno.ilike(f"%{search}%"),
        ))
    if manazer:
        q = q.where(Project.manazer == manazer)
    if kreditny is not None:
        q = q.where(Project.projekt_kreditny == kreditny)
    if zberny is not None:
        q = q.where(Project.projekt_zberny == zberny)
    if kniha is not None:
        q = q.where(Project.projekt_kniha == kniha)
    if cp is not None:
        q = q.where(Project.projekt_cp == cp)
    if oznaceny is not None:
        q = q.where(Project.projekt_oznaceny == oznaceny)
    if cakajuci is not None:
        q = q.where(Project.projekt_cakajuci == cakajuci)
    if bezny is not None:
        q = q.where(Project.projekt_bezny == bezny)
    if hotovo is not None:
        q = q.where(Project.projekt_hotovo == hotovo)
    if expedovat is not None:
        q = q.where(Project.projekt_expedovat == expedovat)
    if sledovany is not None:
        q = q.where(Project.projekt_sledovany == sledovany)
    q = q.order_by(Project.id.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


@router.post("")
async def create_project(data: dict, db: AsyncSession = Depends(get_db)):
    project = Project(**data)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.put("/{project_id}")
async def update_project(project_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        return {"error": "not found"}
    for k, v in data.items():
        if hasattr(project, k):
            setattr(project, k, v)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project:
        await db.delete(project)
        await db.commit()
    return {"ok": True}
