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
    if not settings.N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL not set, skipping forward.")
        return

    async with httpx.AsyncClient() as client:
        try:
            await client.post(settings.N8N_WEBHOOK_URL, json=payload, timeout=10.0)
        except Exception as e:
            logger.error(f"Failed to forward to n8n: {e}")

async def process_incoming_message(payload: Dict[str, Any], db: AsyncSession):
    """
    Extract message from payload and save to DB.
    """
    try:
        print(f"WEBHOOK PAYLOAD: {payload}") # DEBUG LOG
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            print(f"WEBHOOK MESSAGE: {msg}") # DEBUG LOG
            phone = msg.get("from")
            msg_type = msg.get("type")
            content = None
            
            if msg_type == "text":
                content = msg.get("text", {}).get("body")
            elif msg_type == "image":
                content = msg.get("image", {}).get("id")
            
            print(f"EXTRACTED: Phone={phone}, Type={msg_type}, Content={content}") # DEBUG LOG

            if phone and content:
                chat_msg = ChatMessage(
                    customer_phone=phone,
                    sender="user",
                    message_type=msg_type,
                    content=content
                )
                db.add(chat_msg)
                await db.commit()
                print("MESSAGE SAVED TO DB!") # DEBUG LOG
            else:
                print("MESSAGE SKIPPED (No content or phone)")
        else:
            print("NO MESSAGES IN PAYLOAD")
                
    except Exception as e:
        print(f"ERROR PROCESSING WEBHOOK: {e}")
        logger.error(f"Error processing webhook payload: {e}")

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
