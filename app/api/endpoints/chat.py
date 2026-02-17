from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.chat import ChatMessage
from app.models.customers import Customer
from app.schemas.chat import ChatMessageRead, ChatMessageCreate, ChatCustomerSummary

router = APIRouter()

@router.get("/customers", response_model=List[ChatCustomerSummary])
async def get_chat_customers(db: AsyncSession = Depends(get_db)):
    """
    List customers who have chat history, enriched with Customer details if available.
    For now, we'll list ALL customers from the Customer table for the UI requirement,
    or we can list distinct phones from chats. 
    User said: "tabla con todos los usuarios". Let's return all Customers from DB.
    """
    result = await db.execute(select(Customer))
    customers = result.scalars().all()
    
    # In a real scenario, we might want to check if they actually have chats, 
    # but the requirement implies a master list of users to access their potential chat.
    # If "usuarios" means interacting users (even without profile), we'd need a union.
    # Given the "ID, Name, Correo" requirement, it strongly aligns with `Customer` model.
    
    summary_list = []
    for c in customers:
        summary_list.append(ChatCustomerSummary(
            phone=c.phone or "N/A", # Phone is the ID
            name=c.full_name,
            email=c.email
        ))
    return summary_list

@router.get("/{phone}/history", response_model=List[ChatMessageRead])
async def get_chat_history(
    phone: str,
    date_filter: Optional[str] = Query(None, description="Format YYYY-MM-DD"),
    text_search: Optional[str] = Query(None, description="Search text content"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat history for a phone number.
    Sorted Newest to Oldest.
    """
    query = select(ChatMessage).where(ChatMessage.customer_phone == phone).order_by(desc(ChatMessage.created_at))
    
    # Filter by date if provided
    if date_filter:
        try:
            # Parse YYYY-MM-DD (standard HTML date input)
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            start_dt = datetime.combine(filter_date, datetime.min.time())
            end_dt = datetime.combine(filter_date, datetime.max.time())
            query = query.where(ChatMessage.created_at >= start_dt, ChatMessage.created_at <= end_dt)
        except ValueError:
            pass # Ignore invalid date format

    # Filter by text content if provided
    if text_search:
        # Case insensitive search
        query = query.where(ChatMessage.content.ilike(f"%{text_search}%"))

    result = await db.execute(query)
    messages = result.scalars().all()
    return messages

@router.post("/", response_model=ChatMessageRead)
async def create_message(
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    msg = ChatMessage(**message.dict())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg
