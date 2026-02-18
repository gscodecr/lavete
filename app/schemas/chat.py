from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ChatMessageBase(BaseModel):
    customer_phone: str
    sender: str  # 'user' or 'ai'
    message_type: str = "text"
    content: Optional[str] = None

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageRead(ChatMessageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ChatCustomerSummary(BaseModel):
    phone: str
    name: Optional[str] = None
    email: Optional[str] = None
    last_message: Optional[str] = None
    last_interaction: Optional[datetime] = None
