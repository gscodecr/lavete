from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Pet, Customer, User
from app.schemas import customers
from app.api import deps

router = APIRouter()

@router.get("/{pet_id}", response_model=customers.Pet)
async def read_pet(
    pet_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Pet).where(Pet.id == pet_id))
    pet = result.scalars().first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
    return pet

@router.put("/{pet_id}", response_model=customers.Pet)
async def update_pet(
    pet_id: int,
    pet_in: customers.PetUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Pet).where(Pet.id == pet_id))
    pet = result.scalars().first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")

    update_data = pet_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pet, field, value)

    db.add(pet)
    await db.commit()
    await db.refresh(pet)
    return pet

@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    pet_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Pet).where(Pet.id == pet_id))
    pet = result.scalars().first()
    if not pet:
        raise HTTPException(status_code=404, detail="Pet not found")
        
    await db.delete(pet)
    await db.commit()
