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

@router.get("/phone/{phone}", response_model=customers.Customer, summary="Get Customer by Phone", description="Retrieve a customer details. If not found, CREATES a new customer using the provided name.", responses={201: {"description": "Customer created"}, 200: {"description": "Customer found"}})
async def read_customer_by_phone(
    phone: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user),
    name: Optional[str] = None
):
    from app.models.orders import Order, OrderItem
    
    # Handle optional country code (506)
    phones_to_check = [phone]
    clean_phone = phone
    if phone.startswith("506") and len(phone) > 8:
        clean_phone = phone[3:]
        phones_to_check.append(clean_phone)
    
    query = select(Customer).where(Customer.phone.in_(phones_to_check))
    query = query.options(
        selectinload(Customer.orders).selectinload(Order.items).selectinload(OrderItem.product),
        selectinload(Customer.pets)
    )
    
    result = await db.execute(query)
    customer = result.scalars().first()
    
    if not customer:
        # Create new customer logic if not found
        # Prefer the clean phone (8 digits) for storage if possible
        new_customer = Customer(
            phone=clean_phone,
            full_name=name or "Cliente Nuevo", # Default name if not provided
            email=None, 
            is_active=True
        )
        db.add(new_customer)
        await db.commit()
        await db.refresh(new_customer)
        return new_customer
        
    return customer

@router.get("/{phone}", response_model=customers.Customer)
async def read_customer(
    phone: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # Handle optional country code (506)
    phones_to_check = [phone]
    if phone.startswith("506") and len(phone) > 8:
        phones_to_check.append(phone[3:])

    # We need to fetch pets as well, likely lazy loading will work if session is open
    result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
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
    # Handle optional country code (506)
    phones_to_check = [phone]
    if phone.startswith("506") and len(phone) > 8:
        phones_to_check.append(phone[3:])

    result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
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
    # Handle optional country code (506)
    phones_to_check = [phone]
    if phone.startswith("506") and len(phone) > 8:
        phones_to_check.append(phone[3:])

    result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
    customer = result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = customer_in.model_dump(exclude_unset=True)
    
    # Prevent phone update (it's the ID)
    if "phone" in update_data:
        if update_data["phone"] != customer.phone:
            raise HTTPException(status_code=400, detail="No se puede actualizar el número de teléfono (Identificador único).")
        else:
            del update_data["phone"]

    # Handle Pets Update
    if "pets" in update_data and update_data["pets"] is not None:
        pets_data = update_data.pop("pets")
        # We can either replace all, or update/add using name match. 
        # Given the AI context, likely it sends the updated list.
        # Let's simple strategy: Update if name exists, Add if not.
        
        # Load existing pets
        result_pets = await db.execute(select(Pet).where(Pet.customer_id == customer.id))
        existing_pets = result_pets.scalars().all()
        existing_pets_map = {p.name.lower(): p for p in existing_pets}
        
        for p_data in pets_data:
            # p_data is a dict from model_dump
            p_name = p_data.get("name")
            if not p_name: continue
            
            if p_name.lower() in existing_pets_map:
                # Update existing
                pet = existing_pets_map[p_name.lower()]
                for k, v in p_data.items():
                    if v is not None:
                        setattr(pet, k, v)
                db.add(pet)
            else:
                # Create new
                new_pet = Pet(**p_data, customer_id=customer.id)
                db.add(new_pet)

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
    # Handle optional country code (506)
    phones_to_check = [phone]
    if phone.startswith("506") and len(phone) > 8:
        phones_to_check.append(phone[3:])

    result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
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
    
    # Handle optional country code (506)
    phones_to_check = [phone]
    if phone.startswith("506") and len(phone) > 8:
        phones_to_check.append(phone[3:])

    result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
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
