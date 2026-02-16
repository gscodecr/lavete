from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.models import Customer, Pet, User
from app.schemas import customers
from app.api import deps

router = APIRouter()

# Customers
@router.get("/", response_model=List[customers.Customer])
async def read_customers(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Customer)
    if search:
        query = query.where(
            or_(
                Customer.full_name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%")
            )
        )
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    # Eager loading might be needed if not handled by relationship default, but let's try basic first
    return result.scalars().unique().all() # unique() for relationships

@router.post("/", response_model=customers.Customer)
async def create_customer(
    customer_in: customers.CustomerCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    db_customer = Customer(**customer_in.model_dump())
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    await db.refresh(db_customer)
    return db_customer

@router.get("/{customer_id}", response_model=customers.Customer)
async def read_customer(
    customer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # We need to fetch pets as well, likely lazy loading will work if session is open
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# Pets (Nested under customers or standalone? Let's do nested route or separate)
# For simplicity, separate endpoint but linked validation

@router.post("/{customer_id}/pets", response_model=customers.Pet)
async def create_pet(
    customer_id: int,
    pet_in: customers.PetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    db_pet = Pet(**pet_in.model_dump(), customer_id=customer_id)
    db.add(db_pet)
    await db.commit()
    await db.refresh(db_pet)
    return db_pet
