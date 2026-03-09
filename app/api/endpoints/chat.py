from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.chat import ChatMessage
from app.models.customers import Customer
from app.schemas.chat import ChatMessageRead, ChatMessageCreate, ChatCustomerSummary
from app.core.config import settings

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
            email=c.email,
            ai_active=c.ai_active
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
    # Handle optional country code dynamically
    country_code = settings.COUNTRY_PHONE_CODE
    phones_to_check = [phone]
    if phone.startswith(country_code) and len(phone) > len(country_code):
        phones_to_check.append(phone[len(country_code):])
    else:
        phones_to_check.append(f"{country_code}{phone}")
        
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
    
    # Fix old or incorrect media URLs dynamically for display
    for m in messages:
        if m.content and m.message_type in ["image", "audio", "document"]:
            if "api/v1/chat/media" in m.content and f"{settings.APP_ROOT_PATH}/api/v1/" not in m.content:
                # Provide an absolute path starting with APP_ROOT_PATH
                m.content = m.content.replace("api/v1/chat/media", f"{settings.APP_ROOT_PATH.lstrip('/')}/api/v1/chat/media")
                
    return messages

@router.post("/", response_model=ChatMessageRead)
async def create_message(
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    if message.content and message.message_type in ["image", "audio", "document"]:
        if "api/v1/chat/media" in message.content and f"{settings.APP_ROOT_PATH}/api/v1/" not in message.content:
            message.content = message.content.replace("api/v1/chat/media", f"{settings.APP_ROOT_PATH.lstrip('/')}/api/v1/chat/media")
            
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
    # Fix media URL to ensure absolute path works for WhatsApp and is saved correctly
    if message.content and message.message_type in ["image", "audio", "document"]:
        if "api/v1/chat/media" in message.content and f"{settings.APP_ROOT_PATH}/api/v1/" not in message.content:
            message.content = message.content.replace("api/v1/chat/media", f"{settings.APP_ROOT_PATH.lstrip('/')}/api/v1/chat/media")

    # 1. Log to DB FIRST
    # So even if Meta fails, we see what the AI tried to send
    # Ensure sender is set/defaulted if not passed, usually n8n sends 'ai'
    if not message.sender:
        message.sender = "ai"
        
    msg = ChatMessage(**message.dict())
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # 2. Send to Meta
    from app.core.whatsapp import whatsapp_client
    
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

    return msg

@router.post("/{phone}/ai_toggle")
async def toggle_ai(
    phone: str,
    active: bool,
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle AI responses for a specific customer.
    """
    # Handle incoming phone formats
    phones_to_check = [phone]
    if phone.startswith("506") and len(phone) > 8:
        phones_to_check.append(phone[3:])
    elif len(phone) == 8:
        phones_to_check.append(f"506{phone}")
        
    result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
    customer = result.scalars().first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    customer.ai_active = active
    await db.commit()
    return {"message": f"AI toggled to {active}", "ai_active": active}

from pydantic import BaseModel
class AdminMessageCreate(BaseModel):
    content: str
    message_type: str = "text"

@router.post("/{phone}/admin_send", response_model=ChatMessageRead)
async def send_admin_message(
    phone: str,
    message: AdminMessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message as an Admin directly from the UI.
    """
    # 1. Send via WhatsApp FIRST
    from app.core.whatsapp import whatsapp_client
    try:
        await whatsapp_client.send_message(
            to=phone,
            content=message.content,
            message_type=message.message_type
        )
    except Exception as e:
        # If the send fails (e.g. 24 hour window), do not save to DB.
        # WhatsApp API errors usually get wrapped in HTTPException from whatsapp_client or throw here.
        error_msg = str(e.detail) if hasattr(e, 'detail') else str(e)
        raise HTTPException(status_code=400, detail=f"Error de WhatsApp: El mensaje no pudo ser entregado. (Posiblemente han pasado más de 24 horas). Detalle: {error_msg}")

    # 2. Log to DB as Admin ONLY if successful
    chat_message = ChatMessage(
        customer_phone=phone,
        sender="admin",
        message_type=message.message_type,
        content=message.content
    )
    db.add(chat_message)
    await db.commit()
    await db.refresh(chat_message)

    return chat_message

class AdminTemplateCreate(BaseModel):
    template_name: str
    language_code: str = "es"
    display_text: Optional[str] = None

@router.post("/{phone}/admin_send_template", response_model=ChatMessageRead)
async def send_admin_template(
    phone: str,
    message: AdminTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a pre-approved template message as an Admin directly from the UI.
    """
    # 1. Send via WhatsApp FIRST
    from app.core.whatsapp import whatsapp_client
    try:
        await whatsapp_client.send_template_message(
            to=phone,
            template_name=message.template_name,
            language_code=message.language_code
        )
    except Exception as e:
        error_msg = str(e.detail) if hasattr(e, 'detail') else str(e)
        raise HTTPException(status_code=400, detail=f"Error al enviar plantilla. Verifica que el nombre sea correcto y esté aprobada en Meta. Detalle: {error_msg}")

    # 2. Log to DB as Admin ONLY if successful
    # Create a nice readable string for the chat history
    display_content = message.display_text if message.display_text else f"[Plantilla enviada: {message.template_name}]"
    
    chat_message = ChatMessage(
        customer_phone=phone,
        sender="admin",
        message_type="template",
        content=display_content
    )
    db.add(chat_message)
    await db.commit()
    await db.refresh(chat_message)

    return chat_message

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
        
    return {"url": f"{settings.APP_ROOT_PATH}/api/v1/chat/media/{filename}", "filename": filename, "content_type": file.content_type}

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
