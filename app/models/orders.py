from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=True)
    status = Column(String, default="created", index=True, nullable=False) 
    # created, pending_payment, paid, cancelled, refunded
    total_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    payment_method = Column(String, nullable=True) # sinpe, cash, card
    payment_proof = Column(String, nullable=True) # file path or ID
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_via = Column(String, default="web") # web, whatsapp
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="orders", lazy="selectin")
    pet = relationship("Pet", back_populates="orders", lazy="selectin")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    created_by = relationship("User", lazy="selectin")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_at_moment = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items", lazy="selectin")
