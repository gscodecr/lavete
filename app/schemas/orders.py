from pydantic import BaseModel, condecimal
from typing import Optional, List
from datetime import datetime
from app.schemas.customers import Customer
from app.schemas.products import Product

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    unit_price_at_moment: condecimal(max_digits=10, decimal_places=2) # type: ignore
    subtotal: condecimal(max_digits=10, decimal_places=2) # type: ignore
    
    # Optional nested product for display
    product: Optional[Product] = None

    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    customer_id: int
    pet_id: Optional[int] = None
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    created_via: Optional[str] = "web"

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_method: Optional[str] = None
    payment_proof: Optional[str] = None

class Order(OrderBase):
    id: int
    status: str
    total_amount: condecimal(max_digits=10, decimal_places=2) # type: ignore
    payment_method: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    items: List[OrderItem] = []
    customer: Optional[Customer] = None

    class Config:
        from_attributes = True
