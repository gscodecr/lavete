from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Order, OrderItem, Product, Customer, InventoryMovement, User
from app.schemas import orders
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[orders.Order])
async def read_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Order).options(selectinload(Order.customer), selectinload(Order.items))
    if status:
        query = query.where(Order.status == status)
    
    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=orders.Order)
async def create_order(
    order_in: orders.OrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # Verify customer
    customer = await db.get(Customer, order_in.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    db_order = Order(
        customer_id=order_in.customer_id,
        pet_id=order_in.pet_id,
        status="created",
        total_amount=0,
        created_by_user_id=current_user.id,
        created_via=order_in.created_via
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)
    return db_order

@router.post("/{order_id}/items", response_model=orders.Order)
async def add_order_item(
    order_id: int,
    item_in: orders.OrderItemCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "created":
        raise HTTPException(status_code=400, detail="Cannot add items to initialized order")
        
    product = await db.get(Product, item_in.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.stock < item_in.quantity:
        raise HTTPException(status_code=400, detail=f"Insufficient stock. Available: {product.stock}")
        
    # Create Item
    subtotal = product.price * item_in.quantity
    db_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=item_in.quantity,
        unit_price_at_moment=product.price,
        subtotal=subtotal
    )
    db.add(db_item)
    
    # Update Order Total
    order.total_amount += subtotal
    
    await db.commit()
    # Refresh logic might be tricky with relationships, let's re-fetch with loading
    
    query = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    result = await db.execute(query)
    return result.scalars().first()

@router.post("/{order_id}/confirm", response_model=orders.Order)
async def confirm_order(
    order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    # Eager load items and products to lock/check stock
    query = select(Order).where(Order.id == order_id).options(
        selectinload(Order.items).selectinload(OrderItem.product)
    )
    result = await db.execute(query)
    order = result.scalars().first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "created":
        raise HTTPException(status_code=400, detail="Order already confirmed or cancelled")
        
    # Transactional Check & Update
    # Note: For strict concurrency we might need `with_for_update` on products, 
    # but for this MVP standard check is okay or we can add it.
    
    for item in order.items:
        # Re-check stock
        if item.product.stock < item.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Stock changed for {item.product.name}. Available: {item.product.stock}"
            )
        
        # Deduct stock
        item.product.stock -= item.quantity
        
        # Log movement
        movement = InventoryMovement(
            product_id=item.product.id,
            type="out",
            quantity=item.quantity,
            reason=f"Order #{order.id}",
            created_by_user_id=current_user.id
        )
        db.add(movement)
        
    order.status = "pending_payment"
    await db.commit()
    
    # Re-fetch with all relationships loaded to avoid MissingGreenlet during serialization
    # refresh() is shallow and might expire relationships
    result = await db.execute(query)
    order = result.scalars().first()
    return order
