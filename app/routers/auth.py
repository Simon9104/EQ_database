import os
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET_KEY = os.environ.get("EQ_SECRET_KEY", "eq-projekty-secret-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode()[:72], hashed.encode())
    except Exception:
        return False


def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": str(user_id), "username": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    eq_token: Optional[str] = Cookie(default=None),
) -> User:
    token = eq_token or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nie ste prihlásený")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Neplatný token")
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Používateľ neexistuje alebo je deaktivovaný")
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Nemáte oprávnenie admina")
    return user


@router.post("/login")
async def login(data: dict, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    from app.main import check_rate_limit
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Príliš veľa pokusov. Skúste znova za minútu.")
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nesprávne meno alebo heslo")
    if not user.password_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Heslo nebolo nastavené. Kontaktujte administrátora.")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nesprávne meno alebo heslo")
    token = create_token(user.id, user.username)
    response.set_cookie(
        "eq_token", token,
        httponly=True, samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    )
    return {"ok": True, "user": {"id": user.id, "username": user.username, "plne_meno": user.plne_meno, "is_admin": user.is_admin}}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("eq_token")
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "plne_meno": user.plne_meno, "is_admin": user.is_admin}


@router.get("/users")
async def list_users(user: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username, "plne_meno": u.plne_meno, "is_admin": u.is_admin, "active": u.active, "has_password": bool(u.password_hash)} for u in users]


@router.post("/users/{uid}/set-password")
async def set_password(uid: int, data: dict, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Používateľ nenájdený")
    password = data.get("password") or ""
    if len(password) < 4:
        raise HTTPException(400, "Heslo musí mať aspoň 4 znaky")
    user.password_hash = hash_password(password)
    await db.commit()
    return {"ok": True}


@router.post("/users")
async def create_user(data: dict, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    username = (data.get("username") or "").strip()
    plne_meno = (data.get("plne_meno") or "").strip()
    password = data.get("password") or ""
    if not username:
        raise HTTPException(400, "Meno používateľa je povinné")
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Používateľ '{username}' už existuje")
    if password and len(password) < 4:
        raise HTTPException(400, "Heslo musí mať aspoň 4 znaky")
    user = User(
        username=username,
        plne_meno=plne_meno or username,
        password_hash=hash_password(password) if password else None,
        is_admin=bool(data.get("is_admin")),
        active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"ok": True, "id": user.id, "username": user.username}


@router.put("/users/{uid}")
async def update_user(uid: int, data: dict, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Používateľ nenájdený")
    if "username" in data:
        username = (data["username"] or "").strip()
        if not username:
            raise HTTPException(400, "Meno používateľa je povinné")
        conflict = await db.execute(select(User).where(User.username == username, User.id != uid))
        if conflict.scalar_one_or_none():
            raise HTTPException(400, f"Používateľ '{username}' už existuje")
        user.username = username
    if "plne_meno" in data:
        user.plne_meno = (data["plne_meno"] or "").strip()
    await db.commit()
    return {"ok": True}


@router.post("/users/{uid}/toggle-admin")
async def toggle_admin(uid: int, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Používateľ nenájdený")
    user.is_admin = not user.is_admin
    await db.commit()
    return {"ok": True, "is_admin": user.is_admin}


@router.post("/users/{uid}/toggle-active")
async def toggle_active(uid: int, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Používateľ nenájdený")
    user.active = not user.active
    await db.commit()
    return {"ok": True, "active": user.active}


@router.post("/set-active-project")
async def set_active_project(data: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Track which project the current user has open."""
    result = await db.execute(select(User).where(User.id == user.id))
    u = result.scalar_one()
    u.aktualny_projekt = data.get("projekt_id")
    await db.commit()
    return {"ok": True}


@router.get("/active-users")
async def active_users(db: AsyncSession = Depends(get_db)):
    """Return users with an active project open (for multi-user awareness)."""
    result = await db.execute(
        select(User).where(User.active == True, User.aktualny_projekt != None)
    )
    users = result.scalars().all()
    return [{"id": u.id, "username": u.username, "plne_meno": u.plne_meno, "aktualny_projekt": u.aktualny_projekt} for u in users]


@router.post("/change-password")
async def change_password(data: dict, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    old = data.get("old_password") or ""
    new = data.get("new_password") or ""
    if user.password_hash and not verify_password(old, user.password_hash):
        raise HTTPException(400, "Staré heslo je nesprávne")
    if len(new) < 4:
        raise HTTPException(400, "Nové heslo musí mať aspoň 4 znaky")
    result = await db.execute(select(User).where(User.id == user.id))
    u = result.scalar_one()
    u.password_hash = hash_password(new)
    await db.commit()
    return {"ok": True}


async def ensure_default_admin(db: AsyncSession):
    """Create default admin if no users have passwords yet."""
    result = await db.execute(select(User).where(User.password_hash != None))
    existing = result.scalars().first()
    if existing:
        return
    # Check if any user exists at all
    result2 = await db.execute(select(User))
    first = result2.scalars().first()
    if first:
        first.password_hash = hash_password("admin")
        first.is_admin = True
        first.active = True
        await db.commit()
        print(f"[AUTH] Default admin set: username='{first.username}' password='admin' — change immediately!")
    else:
        # Create a fallback admin account
        admin = User(username="admin", plne_meno="Administrátor", password_hash=hash_password("admin"), is_admin=True, active=True)
        db.add(admin)
        await db.commit()
        print("[AUTH] Created default admin: username='admin' password='admin' — change immediately!")
