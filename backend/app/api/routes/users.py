from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import UserCreate, UserOut
from app.db.models import User
from app.platform.current_user import get_current_user_id
from app.db.session import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_current_user(db: AsyncSession = Depends(get_db)) -> UserOut:
    """Return the active platform user (pre-SSO dev mode)."""
    user = await db.get(User, get_current_user_id())
    if user is None:
        raise HTTPException(status_code=404, detail="Platform user not found")
    return UserOut(id=user.id, email=user.email, name=user.name)


@router.post("", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)) -> UserOut:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(email=body.email, name=body.name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut(id=user.id, email=user.email, name=user.name)
