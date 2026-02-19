from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, Text, FetchedValue, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    category = Column(String, index=True, nullable=False)
    brand = Column(String, index=True, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    cost = Column(Numeric(10, 2), nullable=True)
    stock = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=5, nullable=False)
    is_active = Column(Boolean, default=True)
    image_url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    target_animals = Column(JSON, default=list) # List of strings e.g. ["Perro", "Gato"]
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory_movements = relationship("InventoryMovement", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(String, nullable=False)  # in, out, adjustment
    quantity = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="inventory_movements")
    created_by = relationship("User")

class InventoryConfig(Base):
    __tablename__ = "inventory_config"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, default="Mi Negocio")
    store_addresses = Column(JSON, default=list) 
    account_number = Column(String, nullable=True)
    sinpe_number = Column(String, nullable=True)
    customer_service_phone = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
