from pydantic import BaseModel, Field, condecimal
from typing import Optional
from datetime import datetime

class ProductBase(BaseModel):
    sku: str
    name: str
    category: str
    brand: Optional[str] = None
    price: condecimal(max_digits=10, decimal_places=2) # type: ignore
    cost: Optional[condecimal(max_digits=10, decimal_places=2)] = None # type: ignore
    stock: int = 0
    min_stock: int = 5
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[condecimal(max_digits=10, decimal_places=2)] = None # type: ignore
    cost: Optional[condecimal(max_digits=10, decimal_places=2)] = None # type: ignore
    stock: Optional[int] = None
    min_stock: Optional[int] = None
    is_active: Optional[bool] = None

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
