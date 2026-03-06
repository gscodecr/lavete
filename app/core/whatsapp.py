import httpx
from app.core.config import settings

class WhatsAppClient:
    def __init__(self):
        self.token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.base_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def send_message(self, to: str, content: str, message_type: str = "text"):
        """
        Send a message to a WhatsApp user.
        Ensures '506' prefix is added to the phone number if missing.
        """
        # Ensure 506 prefix
        if not to.startswith("506"):
            to = f"506{to}"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",  # Default to text for now, extendable later
            "text": {"body": content}
        }

        # Handle image type if needed later
        if message_type == "image":
            payload["type"] = "image"
            payload["image"] = {"link": content}
            del payload["text"]

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                print(f"WhatsApp API Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def send_template_message(self, to: str, template_name: str, language_code: str = "es", components: list = None):
        """
        Send a pre-approved template message to a WhatsApp user.
        """
        # Ensure 506 prefix
        if not to.startswith("506"):
            to = f"506{to}"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if components:
            payload["template"]["components"] = components

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                print(f"WhatsApp API Template Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def send_interactive_buttons(self, to: str, body_text: str, buttons: list[dict]):
        """
        Send an interactive message with up to 3 buttons.
        buttons should be a list of dicts: [{"id": "btn_1", "title": "Yes"}, ...]
        """
        if not to.startswith("506"):
            to = f"506{to}"

        # WhatsApp API requires buttons to be formatted in a specific way
        action_buttons = []
        for btn in buttons[:3]: # Max 3 buttons
            action_buttons.append({
                "type": "reply",
                "reply": {
                    "id": btn.get("id"),
                    "title": btn.get("title")[:20] # WhatsApp limit is usually 20 chars
                }
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body_text
                },
                "action": {
                    "buttons": action_buttons
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                print(f"WhatsApp API Interactive Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def send_interactive_list(self, to: str, body_text: str, button_text: str, sections: list[dict]):
        """
        Send an interactive list message.
        sections should be a list of dicts: [{"title": "Section Title", "rows": [{"id": "row_1", "title": "Row Title", "description": "Row desc"}]}]
        """
        if not to.startswith("506"):
            to = f"506{to}"

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {
                    "text": body_text
                },
                "action": {
                    "button": button_text[:20],
                    "sections": sections
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=self.headers)
            try:
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                print(f"WhatsApp API List Error: {error_detail}")
                from fastapi import HTTPException
                raise HTTPException(status_code=e.response.status_code, detail=f"WhatsApp API Error: {error_detail}")

    async def get_media_url(self, media_id: str):
        """
        Get the temporary URL for a media object.
        """
        url = f"https://graph.facebook.com/v17.0/{media_id}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("url")

    async def download_media(self, media_url: str):
        """
        Download binary content from WhatsApp Media URL.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(media_url, headers=self.headers)
            response.raise_for_status()
            return response.content

whatsapp_client = WhatsAppClient()
