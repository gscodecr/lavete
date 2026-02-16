from typing import Any, List, Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api import deps
from app.core.database import get_db
from app.models.users import User
from app.schemas import users
from app.core.security import get_password_hash

router = APIRouter()

@router.get("/", response_model=List[users.User])
async def read_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Retrieve users. Only for admins.
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=users.User)
async def create_user(
    *,
    db: Annotated[AsyncSession, Depends(get_db)],
    user_in: users.UserCreate,
    current_user: User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Create new user. Only for admins.
    """
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this user name already exists in the system.",
        )
    
    user_data = user_in.model_dump()
    password = user_data.pop("password")
    user_data["password_hash"] = get_password_hash(password)
    
    db_user = User(**user_data)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user
