from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum

class MessageSender(str, enum.Enum):
    USER = "user"
    AI = "ai"

class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    customer_phone = Column(String, index=True, nullable=False) # Linked by phone, not necessarily foreign key if guest
    sender = Column(String, nullable=False) # 'user' or 'ai'
    message_type = Column(String, default="text") # 'text', 'image', 'audio'
    content = Column(Text, nullable=True) # Text content or Image URL
    created_at = Column(DateTime, default=datetime.utcnow)

    # Optional: Link to Customer if they exist in our DB
    # customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    # customer = relationship("Customer")
