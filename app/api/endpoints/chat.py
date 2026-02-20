from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
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
    # Handle optional country code (506) - Search both formats
    phones_to_check = [phone]
    if phone.startswith("506") and len(phone) > 8:
        phones_to_check.append(phone[3:])
    elif len(phone) == 8: # If we get 8 digits, also check 506 version
         phones_to_check.append(f"506{phone}")

    query = select(ChatMessage).where(ChatMessage.customer_phone.in_(phones_to_check)).order_by(desc(ChatMessage.created_at))
    
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

@router.post("/send", response_model=ChatMessageRead)
async def send_message_api(
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message via WhatsApp (Triggered by n8n).
    Logs to DB as 'ai' (usually) and sends to Meta.
    """
    # 1. Send to Meta
    from app.core.whatsapp import whatsapp_client
    
    # Ensure sender is set/defaulted if not passed, usually n8n sends 'ai'
    # but we trust the input payload.
    
    try:
        await whatsapp_client.send_message(
            to=message.customer_phone,
            content=message.content,
            message_type=message.message_type
        )
    except Exception as e:
        # If send fails, should we still log? 
        # Yes, maybe log as failed? Model doesn't have status.
        # Let's error out for now so n8n knows it failed.
        raise HTTPException(status_code=500, detail=str(e))

    # 2. Log to DB
    msg = ChatMessage(**message.dict())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
):
    """
    Upload media file (image, audio, document) for chat.
    Returns the URL to access the file.
    """
    import shutil
    import os
    import uuid
    
    # Ensure directory exists
    UPLOAD_DIR = "app/static/chat_uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    if not ext:
        ext = ".bin"
        
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        
    return {"url": f"/lavete/api/v1/chat/media/{filename}", "filename": filename, "content_type": file.content_type}

@router.get("/media/{filename}")
async def get_media(filename: str):
    """
    Serve uploaded media files directly through FastAPI.
    Bypasses Nginx static file configuration issues.
    """
    import os
    from fastapi.responses import FileResponse
    
    UPLOAD_DIR = "app/static/chat_uploads"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(file_path)
