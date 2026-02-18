import sys
import os
import asyncio
import httpx

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings

BASE_URL = "https://graph.facebook.com/v17.0"

async def check_subscription():
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        print("ERROR: WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set in .env")
        return

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    url = f"{BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/subscribed_apps"
    
    print(f"Checking subscription for Phone ID: {settings.WHATSAPP_PHONE_NUMBER_ID}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            print("Current Subscriptions:")
            print(data)
            return data
        except Exception as e:
            print(f"Error checking subscription: {e}")
            if hasattr(e, 'response'):
                 print(e.response.text)

async def subscribe_app():
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    url = f"{BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/subscribed_apps"
    
    print(f"Subscribing App to Phone ID: {settings.WHATSAPP_PHONE_NUMBER_ID}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            print("SUCCESS: App subscribed to Webhooks for this phone number!")
            print(response.json())
        except Exception as e:
            print(f"Error subscribing: {e}")
            if hasattr(e, 'response'):
                 print(e.response.text)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "subscribe":
        asyncio.run(subscribe_app())
    else:
        asyncio.run(check_subscription())
        print("\nTo subscribe, run: python scripts/whatsapp_setup.py subscribe")
