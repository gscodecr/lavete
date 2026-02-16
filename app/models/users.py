from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="staff", nullable=False)  # admin, vet, inventory, staff
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity = Column(String, index=True, nullable=False)
    entity_id = Column(Integer, index=True, nullable=False)
    action = Column(String, nullable=False)  # create, update, delete
    changes = Column(JSON, nullable=True) # stores before/after
    user_id = Column(Integer, index=True, nullable=True) # null if system/whatsapp
    timestamp = Column(DateTime, default=datetime.utcnow)
