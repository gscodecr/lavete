from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
import os
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
    """
    Create a new order. 
    You can optionally pass a list of 'items' to create the order and its items in one transaction.
    """
    # Verify customer and get default address if needed
    customer_result = await db.execute(select(Customer).where(Customer.id == order_in.customer_id))
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    delivery_address = order_in.delivery_address
    if not delivery_address:
        if getattr(customer, 'address', None):
            delivery_address = customer.address
        elif getattr(customer, 'addresses', None) and len(customer.addresses) > 0:
            # Use first address as default if not provided
            addr = customer.addresses[0]
            # Format address nicely based on possible fields
            addr_parts = []
            if addr.get('address'): addr_parts.append(addr.get('address'))
            if addr.get('description'): addr_parts.append(addr.get('description'))
            if addr.get('city'): addr_parts.append(addr.get('city'))
            if addr.get('state'): addr_parts.append(addr.get('state'))
            delivery_address = ", ".join(addr_parts) if addr_parts else str(addr)

    db_order = Order(
        customer_id=order_in.customer_id,
        pet_id=order_in.pet_id,
        status="created",
        total_amount=0,
        payment_method=order_in.payment_method,
        payment_proof=order_in.payment_proof,
        delivery_address=delivery_address,
        created_by_user_id=getattr(current_user, 'id', None),
        created_via=order_in.created_via,
        notes=order_in.notes
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)

    # Process Items if any
    if order_in.items:
        total_amount = 0
        for item in order_in.items:
            product = await db.get(Product, item.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            
            if product.stock < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
                
            subtotal = product.price * item.quantity
            db_item = OrderItem(
                order_id=db_order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price_at_moment=product.price,
                subtotal=subtotal
            )
            db.add(db_item)
            total_amount += subtotal
            
        db_order.total_amount = total_amount
        await db.commit()
        await db.refresh(db_order)
        
    # Validation: Return with items loaded
    query = select(Order).where(Order.id == db_order.id).options(selectinload(Order.items))
    result = await db.execute(query)
    return result.scalars().first()

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

@router.get("/{order_id}", response_model=orders.Order)
async def read_order(
    order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    query = select(Order).where(Order.id == order_id).options(
        selectinload(Order.customer), 
        selectinload(Order.items).selectinload(OrderItem.product)
    )
    result = await db.execute(query)
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.get("/{order_id}/receipt")
async def get_order_receipt(
    order_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get the payment receipt image for an order.
    """
    import os
    from fastapi.responses import FileResponse
    
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if not order.payment_proof:
        raise HTTPException(status_code=404, detail="No receipt found for this order")
        
    # The payment_proof might be stored as an HTTP URL from the WhatsApp webhook
    # like "https://example.com/lavete/api/v1/chat/media/filename.jpg" or "/lavete/..."
    # We need to extract the raw filename to serve from "app/static/chat_uploads"
    filename = order.payment_proof.split('/')[-1]
    
    # Also handle if it somehow stored an absolute file path directly
    if order.payment_proof.startswith('/var/www/lavete/app/static'):
        file_path = order.payment_proof
    else:
        file_path = os.path.join("app/static/chat_uploads", filename)
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Receipt document missing on server ({filename})")
        
    return FileResponse(file_path)

@router.put("/{order_id}", response_model=orders.Order)
async def update_order(
    order_id: int,
    order_in: orders.OrderUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_user) # restrict to admin/seller?
):
    """
    Update an order.
    - Can update status, payment info.
    - Can update 'items' (replace all existing items) ONLY if status is 'created'.
    """
    query = select(Order).where(Order.id == order_id).options(
        selectinload(Order.customer), 
        selectinload(Order.items).selectinload(OrderItem.product)
    )
    result = await db.execute(query)
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = order_in.model_dump(exclude_unset=True)
    
    # Handle Items Update
    if 'items' in update_data and update_data['items'] is not None:
        if order.status != 'created':
            raise HTTPException(status_code=400, detail="Cannot update items of a confirmed/cancelled order")
            
        # Clear existing items
        # We rely on the cascade="all, delete-orphan" to delete from DB
        order.items.clear()
            
        new_items = update_data.pop('items')
        total_amount = 0
        
        for item_data in new_items:
            # We need to access as dict
            product_id = item_data['product_id']
            quantity = item_data['quantity']
            
            product = await db.get(Product, product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
            
            if product.stock < quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
            
            subtotal = product.price * quantity
            db_item = OrderItem(
                product_id=product.id,
                quantity=quantity,
                unit_price_at_moment=product.price,
                subtotal=subtotal
            )
            order.items.append(db_item)
            total_amount += subtotal
            
        order.total_amount = total_amount

    for field, value in update_data.items():
        setattr(order, field, value)

    db.add(order)
    await db.commit()
    
    # Reload with items
    query = select(Order).where(Order.id == order_id).options(
        selectinload(Order.customer), 
        selectinload(Order.items).selectinload(OrderItem.product)
    )
    result = await db.execute(query)
    return result.scalars().first()
