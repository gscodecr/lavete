from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime

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
    notes: Optional[str] = None

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
    created_at: datetime
    items: List[CustomerOrderItem] = []
    
    class Config:
        from_attributes = True

class Customer(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    pets: List[Pet] = []
    orders: List[CustomerOrder] = []
    
    class Config:
        from_attributes = True
