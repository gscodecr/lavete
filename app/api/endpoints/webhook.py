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
    Extract message from payload and save to DB.
    """
    try:
        print(f"REAL WEBHOOK PAYLOAD: {payload}", flush=True) # FORCE LOG
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            print(f"REAL WEBHOOK MSG: {msg}", flush=True) # FORCE LOG
            phone = msg.get("from")
            msg_type = msg.get("type")
            content = None
            
            if msg_type == "text":
                content = msg.get("text", {}).get("body")
            elif msg_type == "image":
                content = msg.get("image", {}).get("id")
            
            if phone and content:
                print(f"SAVING: {phone} - {content}", flush=True) # FORCE LOG
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
