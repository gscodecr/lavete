from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional, List, Any
from datetime import datetime
import os

# Pet Schemas
class PetBase(BaseModel):
    name: str
    species: str
    breed: Optional[str] = None
    birthdate: Optional[datetime] = None
    age_notes: Optional[str] = None
    weight: Optional[str] = None
    allergies: Optional[str] = None
    medical_notes: Optional[str] = None

class PetCreate(PetBase):
    pass

class PetUpdate(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    breed: Optional[str] = None
    birthdate: Optional[datetime] = None
    age_notes: Optional[str] = None
    weight: Optional[str] = None
    allergies: Optional[str] = None
    medical_notes: Optional[str] = None

class Pet(PetBase):
    id: int
    customer_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Customer Schemas
class CustomerBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: bool = True
    addresses: Optional[List[dict]] = None
    default_payment_method: Optional[str] = None
    notes: Optional[str] = None

class CustomerBasic(CustomerBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    addresses: Optional[List[dict]] = None
    default_payment_method: Optional[str] = None
    default_payment_method: Optional[str] = None
    notes: Optional[str] = None
    pets: Optional[List[PetUpdate]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Juan Perez",
                "phone": "88888888",
                "default_payment_method": "Sinpe",
                "is_active": True
            }
        }
    }

class CustomerOrderItemProduct(BaseModel):
    name: str

class CustomerOrderItem(BaseModel):
    product: Optional[CustomerOrderItemProduct] = None
    quantity: int
    unit_price_at_moment: float
    subtotal: float
    
    class Config:
        from_attributes = True

class CustomerOrder(BaseModel):
    id: int
    total_amount: float
    status: str
    payment_method: Optional[str] = None
    payment_proof: Optional[str] = None
    delivery_address: Optional[str] = None
    created_at: datetime
    items: List[CustomerOrderItem] = []
    
    @computed_field
    @property
    def has_payment_receipt(self) -> bool:
        return bool(self.payment_proof)
        
    @computed_field
    @property
    def payment_receipt_url(self) -> Optional[str]:
        if not self.payment_proof:
            return None
        # Assuming the base URL is the host running the API, 
        # return the relative path that the frontend uses to fetch the file
        # The frontend/n8n will prepend the domain
        return f"/api/orders/{self.id}/receipt"

    
    class Config:
        from_attributes = True

class CustomerInteraction(BaseModel):
    sender: str
    message_type: str
    content: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class Customer(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    pets: List[Pet] = []
    orders: List[CustomerOrder] = []
    recent_interactions: List[CustomerInteraction] = []
    
    class Config:
        from_attributes = True
