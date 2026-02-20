from fastapi import APIRouter, Request, Response, BackgroundTasks, Depends
from typing import Dict, Any
import httpx
from app.core.config import settings
from app.core.database import get_db
from app.models.chat import ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Handle Meta's Webhook Verification Challenge.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return Response(content=challenge, media_type="text/plain")
        else:
            return Response(status_code=403, content="Verification failed")
    
    return Response(status_code=400, content="Missing parameters")

async def forward_to_n8n(payload: Dict[str, Any]):
    """
    Forward the incoming payload to n8n.
    """
    url = settings.N8N_WEBHOOK_URL
    print(f"FORWARDING TO N8N: {url}", flush=True) # FORCE LOG
    
    if not url:
        print("ERROR: N8N_WEBHOOK_URL not set in environment!", flush=True)
        return

    async with httpx.AsyncClient() as client:
        try:
            print(f"N8N PAYLOAD: {payload}", flush=True) # FORCE LOG
            response = await client.post(url, json=payload, timeout=10.0)
            print(f"N8N RESPONSE: {response.status_code} - {response.text}", flush=True) # FORCE LOG
        except Exception as e:
            print(f"N8N ERROR: {e}", flush=True)

async def process_incoming_message(payload: Dict[str, Any], db: AsyncSession):
    """
    Extract message from payload, ENSURE CUSTOMER EXISTS, and save message to DB.
    """
    try:
        print(f"REAL WEBHOOK PAYLOAD: {payload}", flush=True) # FORCE LOG
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        contacts = value.get("contacts", [])

        if messages:
            msg = messages[0]
            print(f"REAL WEBHOOK MSG: {msg}", flush=True) # FORCE LOG
            phone = msg.get("from")
            msg_type = msg.get("type")
            
            # Extract Profile Name
            profile_name = "Cliente WhatsApp"
            if contacts:
                profile = contacts[0].get("profile", {})
                profile_name = profile.get("name", "Cliente WhatsApp")
            
            content = None
            if msg_type == "text":
                content = msg.get("text", {}).get("body")
            elif msg_type in ["image", "audio", "document"]:
                # Handle Media
                media_id = msg.get(msg_type, {}).get("id")
                
                # Fetch Media from WhatsApp
                from app.core.whatsapp import whatsapp_client
                import os
                import uuid
                
                try:
                    print(f"DOWNLOADING MEDIA ID: {media_id}", flush=True)
                    media_url = await whatsapp_client.get_media_url(media_id)
                    media_binary = await whatsapp_client.download_media(media_url)
                    
                    # Determine extension
                    mime_type = msg.get(msg_type, {}).get("mime_type", "")
                    ext = ".bin"
                    if "image" in mime_type: ext = ".jpg" # Simplify
                    elif "audio" in mime_type: ext = ".ogg"
                    elif "pdf" in mime_type: ext = ".pdf"
                    
                    # Save to static
                    UPLOAD_DIR = "app/static/chat_uploads"
                    os.makedirs(UPLOAD_DIR, exist_ok=True)
                    
                    filename = f"{uuid.uuid4()}{ext}"
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(media_binary)
                        
                    content = f"/lavete/api/v1/chat/media/{filename}"
                    print(f"MEDIA SAVED: {content}", flush=True)
                    
                except Exception as e:
                    print(f"FAILED TO DOWNLOAD MEDIA: {e}", flush=True)
                    content = f"[ERROR DOWNLOADING MEDIA {msg_type}]"
            
            if phone and content:
                # --- GET OR CREATE CUSTOMER LOGIC START ---
                from app.models.customers import Customer
                from sqlalchemy import select
                
                # Handle 506 prefix logic
                phones_to_check = [phone]
                clean_phone = phone
                if phone.startswith("506") and len(phone) > 8:
                    clean_phone = phone[3:]
                    phones_to_check.append(clean_phone)
                
                # Check exist
                result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
                customer = result.scalars().first()
                
                if not customer:
                    print(f"CREATING NEW CUSTOMER: {profile_name} - {clean_phone}", flush=True)
                    new_customer = Customer(
                        full_name=profile_name,
                        phone=clean_phone,
                        email=None,
                        is_active=True,
                        notes="Creado automáticamente desde WhatsApp"
                    )
                    db.add(new_customer)
                    await db.commit()
                    await db.refresh(new_customer)
                    print(f"CUSTOMER CREATED ID: {new_customer.id}", flush=True)
                else:
                    print(f"CUSTOMER EXISTS: {customer.full_name}", flush=True)
                # --- GET OR CREATE CUSTOMER LOGIC END ---

                print(f"SAVING MSG: {phone} - {content}", flush=True) # FORCE LOG
                chat_msg = ChatMessage(
                    customer_phone=phone,
                    sender="user",
                    message_type=msg_type,
                    content=content
                )
                db.add(chat_msg)
                await db.commit()
                print("SAVED OK", flush=True) # FORCE LOG
    except Exception as e:
        print(f"ERROR: {e}", flush=True)

@router.post("/webhook")
async def receive_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive Webhook from Meta.
    """
    try:
        payload = await request.json()
        
        # 1. Log to DB (User Message)
        # We await this because we want to ensure it's saved? 
        # Or background it? Let's background the processing to return 200 OK fast to Meta.
        # However, passing DB session to background task can be tricky with async dependency injection closing session.
        # For simplicity and robustness in this scale, let's await the DB save (fast enough) and background the n8n forward.
        
        # Actually, let's just inspect payload quickly.
        # Meta expects 200 OK fast.
        
        # IMPORTANT: 'process_incoming_message' needs a session. 
        # Fastapi dependency 'db' is scoped to request. 
        # So we should await it here.
        await process_incoming_message(payload, db)
        
        # 2. Forward to n8n
        background_tasks.add_task(forward_to_n8n, payload)
        
        return Response(status_code=200, content="EVENT_RECEIVED")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        # Always return 200 to Meta to prevent retries loop if it's our bug
        return Response(status_code=200, content="EVENT_RECEIVED_ERROR")
