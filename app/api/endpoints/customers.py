from typing import List, Annotated, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

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
    # We need to import Order and OrderItem to use them in selectinload if they are not available via string or attribute
    # However, SQLAlchemy can often infer from the model class attributes. 
    # But Customer.orders is a relationship to Order. Order.items is a relationship to OrderItem.
    # To chain, we need the classes usually or simpler strings if registry works.
    # Safest is to import them inside or at top.
    from app.models.orders import Order, OrderItem
    
    query = query.options(
        selectinload(Customer.orders).selectinload(Order.items).selectinload(OrderItem.product)
    )
    result = await db.execute(query)
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

@router.get("/phone/{phone}", response_model=customers.Customer, summary="Get Customer by Phone", description="Retrieve a customer details and related orders/pets using their phone number.", responses={404: {"description": "Customer not found"}})
async def read_customer_by_phone(
    phone: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    from app.models.orders import Order, OrderItem
    
    query = select(Customer).where(Customer.phone == phone)
    query = query.options(
        selectinload(Customer.orders).selectinload(Order.items).selectinload(OrderItem.product),
        selectinload(Customer.pets)
    )
    
    result = await db.execute(query)
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.get("/{phone}", response_model=customers.Customer)
async def read_customer(
    phone: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # We need to fetch pets as well, likely lazy loading will work if session is open
    result = await db.execute(select(Customer).where(Customer.phone == phone))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# Pets (Nested under customers or standalone? Let's do nested route or separate)
# For simplicity, separate endpoint but linked validation

@router.post("/{phone}/pets", response_model=customers.Pet)
async def create_pet(
    phone: str,
    pet_in: customers.PetCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Customer).where(Customer.phone == phone))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    db_pet = Pet(**pet_in.model_dump(), customer_id=customer.id)
    db.add(db_pet)
    await db.commit()
    await db.refresh(db_pet)
    return db_pet

@router.put("/{phone}", response_model=customers.Customer)
async def update_customer(
    phone: str,
    customer_in: customers.CustomerUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Customer).where(Customer.phone == phone))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer_in.model_dump(exclude_unset=True)
    
    # Check for phone uniqueness if phone is being updated
    if "phone" in update_data and update_data["phone"] != customer.phone:
        existing_phone = await db.execute(select(Customer).where(Customer.phone == update_data["phone"]))
        if existing_phone.scalars().first():
             raise HTTPException(status_code=400, detail="Phone number already registered")

    for field, value in update_data.items():
        setattr(customer, field, value)

    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer

# Fetch orders for a specific customer
@router.get("/{phone}/orders", response_model=List[dict]) # Return simple dict or create OrderSchema
async def read_customer_orders(
    phone: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    result = await db.execute(select(Customer).where(Customer.phone == phone))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Need to import Order model here or at top
    from app.models.orders import Order
    
    result = await db.execute(select(Order).where(Order.customer_id == customer.id).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    
    # Return simplified list for the frontend table
    return [
        {
            "id": o.id,
            "created_at": o.created_at,
            "status": o.status,
            "total_amount": o.total_amount,
            "items_count": len(o.items) if o.items else 0
        } 
        for o in orders
    ]

@router.delete("/{phone}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    phone: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # Only admins should delete? For now assume verified user is enough or check role
    # if current_user.role != "admin": raise ...
    
    result = await db.execute(select(Customer).where(Customer.phone == phone))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # Check if customer has orders
    # Avoid circular import by doing a direct DB check or importing inside
    from app.models.orders import Order
    
    orders_check = await db.execute(select(Order.id).where(Order.customer_id == customer.id).limit(1))
    if orders_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No se puede eliminar el cliente porque tiene órdenes asociadas. Considere desactivarlo en su lugar."
        )

    await db.delete(customer)
    await db.commit()
