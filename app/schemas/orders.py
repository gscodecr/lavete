from pydantic import BaseModel, condecimal, computed_field
from typing import Optional, List
from datetime import datetime
from app.schemas.customers import CustomerBasic
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
    delivery_address: Optional[str] = None
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    created_via: Optional[str] = "web"
    items: Optional[List[OrderItemCreate]] = []
    payment_method: Optional[str] = None
    payment_proof: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": 1,
                "pet_id": 5,
                "notes": "Urgent delivery",
                "created_via": "whatsapp",
                "items": [
                    {"product_id": 10, "quantity": 2},
                    {"product_id": 15, "quantity": 1}
                ]
            }
        }
    }

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_method: Optional[str] = None
    payment_proof: Optional[str] = None
    delivery_address: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[OrderItemCreate]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "pending_payment",
                "items": [
                    {"product_id": 10, "quantity": 3}
                ]
            }
        }
    }

class Order(OrderBase):
    id: int
    status: str
    total_amount: condecimal(max_digits=10, decimal_places=2) # type: ignore
    payment_method: Optional[str] = None
    payment_proof: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    items: List[OrderItem] = []
    customer: Optional[CustomerBasic] = None

    @computed_field
    @property
    def has_payment_receipt(self) -> bool:
        return bool(self.payment_proof)
        
    @computed_field
    @property
    def payment_receipt_url(self) -> Optional[str]:
        if not self.payment_proof:
            return None
        return f"/api/orders/{self.id}/receipt"

    class Config:
        from_attributes = True
