from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True, nullable=False)
    phone = Column(String, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    addresses = Column(JSON, nullable=True)  # List of address objects
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pets = relationship("Pet", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")
    orders = relationship("Order", back_populates="customer", lazy="selectin")

class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    species = Column(String, nullable=False)  # Perro, Gato, etc.
    breed = Column(String, nullable=True)
    birthdate = Column(DateTime, nullable=True)
    age_notes = Column(String, nullable=True) # e.g. "2 years" if birthdate unknown
    weight = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)
    medical_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("Customer", back_populates="pets")
    orders = relationship("Order", back_populates="pet")
