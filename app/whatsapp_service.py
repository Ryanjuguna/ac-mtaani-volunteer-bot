import os
import httpx
from typing import Optional, Dict, Any, List
from app.config import settings

class WhatsAppService:
    def __init__(self):
        self._provider_override = None
        self.outbox_history: List[Dict[str, Any]] = []

    @property
    def provider(self) -> str:
        return self._provider_override or settings.WHATSAPP_PROVIDER

    @provider.setter
    def provider(self, val: str):
        self._provider_override = val

    @property
    def instance_id(self) -> str:
        return settings.GREEN_API_INSTANCE_ID

    @property
    def token(self) -> str:
        return settings.GREEN_API_TOKEN

    def is_live(self) -> bool:
        return bool(self.provider == "green_api" and self.instance_id and self.token)

    async def send_direct_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Sends a 1-on-1 private WhatsApp message to a volunteer.
        """
        clean_phone = "".join(ch for ch in phone if ch.isdigit())
        chat_id = f"{clean_phone}@c.us"
        
        record = {
            "type": "DM",
            "to": phone,
            "chat_id": chat_id,
            "message": message,
            "status": "SENT"
        }
        self.outbox_history.append(record)
        # Safe print for Windows consoles
        safe_msg = message.encode("ascii", errors="replace").decode("ascii")
        print(f"[WhatsApp DM -> {phone}]:\n{safe_msg}\n")

        # STRICT SAFETY LOCK: Only allow messaging whitelisted test numbers (Coordinator)
        is_whitelisted = False
        clean_target = "".join(ch for ch in phone if ch.isdigit())
        for wp in settings.WHITELISTED_PHONES:
            clean_wp = "".join(ch for ch in str(wp) if ch.isdigit())
            if clean_target and clean_wp and (clean_target.endswith(clean_wp[-9:]) or clean_wp.endswith(clean_target[-9:])):
                is_whitelisted = True
                break

        if not is_whitelisted:
            print(f"[SAFETY LOCK] Outbound message to {phone} was BLOCKED. Real volunteers are protected from test pings.")
            record["status"] = "BLOCKED_BY_SAFETY_LOCK"
            record["gateway_response"] = {
                "blocked": True,
                "reason": f"Phone {phone} is not whitelisted. Live messaging blocked to protect volunteers."
            }
            return record

        if self.is_live():
            url = f"https://api.green-api.com/waInstance{self.instance_id}/sendMessage/{self.token}"
            payload = {"chatId": chat_id, "message": message}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    record["gateway_response"] = resp.json()
            except Exception as e:
                print(f"[WhatsApp Gateway Error]: {e}")
                record["gateway_error"] = str(e)

        return record

    async def send_group_receipt(self, group_chat_id: str, message: str) -> Dict[str, Any]:
        """
        Sends a concise confirmation receipt back to the group chat.
        """
        record = {
            "type": "GROUP_RECEIPT",
            "to": group_chat_id,
            "message": message,
            "status": "SENT"
        }
        self.outbox_history.append(record)
        safe_msg = message.encode("ascii", errors="replace").decode("ascii")
        print(f"[WhatsApp Group Receipt -> {group_chat_id}]: {safe_msg}")

        if self.is_live():
            url = f"https://api.green-api.com/waInstance{self.instance_id}/sendMessage/{self.token}"
            payload = {"chatId": group_chat_id, "message": message}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    record["gateway_response"] = resp.json()
            except Exception as e:
                print(f"[WhatsApp Gateway Group Error]: {e}")
                record["gateway_error"] = str(e)

        return record

    def get_recent_outbox(self) -> List[Dict[str, Any]]:
        return self.outbox_history[-20:]

whatsapp_service = WhatsAppService()
