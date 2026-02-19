from pydantic import BaseModel, Field, condecimal
from typing import Optional, List
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
    is_active: bool = True
    image_url: Optional[str] = None
    description: Optional[str] = None
    target_animals: Optional[List[str]] = []

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
    image_url: Optional[str] = None
    description: Optional[str] = None
    target_animals: Optional[List[str]] = None

class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

from typing import List, Dict, Any

# Inventory Config Schemas
class InventoryConfigBase(BaseModel):
    business_name: Optional[str] = "Mi Negocio"
    store_addresses: Optional[List[Dict[str, Any]]] = [] # List of {name, address, map_pin}
    account_number: Optional[str] = None
    sinpe_number: Optional[str] = None
    customer_service_phone: Optional[str] = None

class InventoryConfigCreate(InventoryConfigBase):
    pass

class InventoryConfigUpdate(InventoryConfigBase):
    pass

class InventoryConfig(InventoryConfigBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class InventoryResponse(BaseModel):
    inventory: List[Product]
    config: Optional[InventoryConfig] = None
