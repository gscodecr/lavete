import sys
import os
import asyncio
import httpx

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings

BASE_URL = "https://graph.facebook.com/v17.0"

async def get_waba_id():
    """
    Fetch the WhatsApp Business Account ID from the Phone Number ID.
    """
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        print("ERROR: WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set in .env")
        return None

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # Get WABA ID
    url = f"{BASE_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}?fields=whatsapp_business_account"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            waba_id = data.get("whatsapp_business_account", {}).get("id")
            if not waba_id:
                print("ERROR: Could not find WABA ID linked to this phone number.")
                print(data)
                return None
            print(f"Found WABA ID: {waba_id} (Linked to Phone ID: {settings.WHATSAPP_PHONE_NUMBER_ID})")
            return waba_id
        except Exception as e:
            print(f"Error fetching WABA ID: {e}")
            if hasattr(e, 'response'):
                 print(e.response.text)
            return None

async def check_subscription():
    waba_id = await get_waba_id()
    if not waba_id:
        return

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    url = f"{BASE_URL}/{waba_id}/subscribed_apps"
    
    print(f"Checking subscription for WABA ID: {waba_id}...")
    
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


async def subscribe_app(waba_id=None):
    if not waba_id:
        waba_id = await get_waba_id()
    
    if not waba_id:
        print("ERROR: Could not determine WABA ID. Please provide it as an argument: python scripts/whatsapp_setup.py subscribe <WABA_ID>")
        return

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    
    url = f"{BASE_URL}/{waba_id}/subscribed_apps"
    
    print(f"Subscribing App to WABA ID: {waba_id}...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            print("SUCCESS: App subscribed to Webhooks for this WABA!")
            print(response.json())
        except Exception as e:
            print(f"Error subscribing: {e}")
            if hasattr(e, 'response'):
                 print(e.response.text)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "subscribe":
        waba_id_arg = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(subscribe_app(waba_id_arg))
    else:
        asyncio.run(check_subscription())
        print("\nTo subscribe, run: python scripts/whatsapp_setup.py subscribe [WABA_ID]")
