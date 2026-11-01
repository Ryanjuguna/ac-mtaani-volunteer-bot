import asyncio
import json
import httpx
from typing import Optional
from app.config import settings
from app.task_engine import task_engine
from app.parser import parser

class GreenApiPoller:
    def __init__(self):
        self.running = False
        self._task: Optional[asyncio.Task] = None

    @property
    def instance_id(self) -> str:
        return settings.GREEN_API_INSTANCE_ID

    @property
    def token(self) -> str:
        return settings.GREEN_API_TOKEN

    def is_configured(self) -> bool:
        return bool(self.instance_id and self.token and settings.WHATSAPP_PROVIDER == "green_api")

    async def start(self):
        if not self.is_configured():
            print("[Poller] Green API not fully configured. Running in local/simulator mode.")
            return

        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(self._poll_loop())
        print(f"[Poller] Background WhatsApp Poller started for Instance: {self.instance_id}")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[Poller] Background WhatsApp Poller stopped.")

    async def _poll_loop(self):
        async with httpx.AsyncClient(timeout=20.0) as client:
            while self.running:
                try:
                    receive_url = f"https://api.green-api.com/waInstance{self.instance_id}/receiveNotification/{self.token}?receiveTimeout=5"
                    delete_url = f"https://api.green-api.com/waInstance{self.instance_id}/deleteNotification/{self.token}"

                    resp = await client.get(receive_url)
                    if resp.status_code == 200 and resp.text.strip():
                        data = resp.json()
                        if data and "receiptId" in data and "body" in data:
                            receipt_id = data["receiptId"]
                            body = data["body"]
                            
                            type_w = body.get("typeWebhook")
                            # Process the incoming notification
                            await self._handle_notification(body)

                            # Delete notification to acknowledge receipt
                            await client.delete(f"{delete_url}/{receipt_id}")
                    
                    await asyncio.sleep(0.5)

                except asyncio.CancelledError:
                    break
                except httpx.ReadTimeout:
                    # Expected timeout when queue is idle
                    continue
                except Exception as e:
                    print(f"[Poller Error]: {e}")
                    await asyncio.sleep(2.0)

    async def _handle_notification(self, body: dict):
        type_webhook = body.get("typeWebhook")
        # 1. Ignore automated messages sent by our bot via API
        if type_webhook == "outgoingAPIMessageReceived" or body.get("sendByApi"):
            return
        # 2. Only process incoming messages or coordinator phone messages
        if type_webhook not in ["incomingMessageReceived", "outgoingMessageReceived"]:
            return

        sender_data = body.get("senderData", {})
        message_data = body.get("messageData", {})

        # Extract chat_id (e.g. 120363430300380977@g.us for group, 254752901669@c.us for DM)
        chat_id = body.get("chatId") or sender_data.get("chatId", "")
        sender_name = body.get("senderName") or sender_data.get("senderName", "WhatsApp User")
        
        # Extract sender phone
        sender_phone_raw = (
            sender_data.get("sender", "") or
            body.get("senderId", "") or
            chat_id
        )
        sender_phone = "".join(ch for ch in sender_phone_raw.split("@")[0] if ch.isdigit())
        if sender_phone and not sender_phone.startswith("+"):
            sender_phone = f"+{sender_phone}"

        # Extract text (nested for incoming, root for outgoing)
        text = (
            body.get("textMessage") or
            message_data.get("textMessageData", {}).get("textMessage") or
            message_data.get("extendedTextMessageData", {}).get("text") or
            ""
        )

        if not text.strip():
            return

        is_group = "@g.us" in chat_id
        has_task = parser.has_trigger(text)

        # Safe print for Windows terminal
        clean_text_preview = text.encode("ascii", errors="replace").decode("ascii")[:60]
        print(f"[Poller Event] {type_webhook} | {'Group' if is_group else 'DM'}: '{clean_text_preview}'")

        # GROUP LOGIC:
        if is_group:
            # In groups, we ONLY react to messages containing @task
            if not has_task:
                return  # Silently ignore general group banter
            
            await task_engine.process_group_message(
                sender_name=sender_name,
                sender_phone=sender_phone,
                text=text,
                chat_id=chat_id
            )
            return

        # DIRECT MESSAGE (1-on-1) LOGIC:
        if has_task:
            # Coordinator assigned a task via direct message or self-chat
            await task_engine.process_group_message(
                sender_name=sender_name,
                sender_phone=sender_phone,
                text=text,
                chat_id=chat_id
            )
        else:
            # Volunteer reply or status check
            # For outgoingMessageReceived in DM:
            # If Ryan typed in self-chat (chat_id is Ryan's number), sender_phone is Ryan.
            # If Ryan typed to another contact, chat_id is the contact. In that case, Ryan is sending to them, so skip.
            if type_webhook == "outgoingMessageReceived":
                clean_chat = "".join(ch for ch in chat_id if ch.isdigit())
                clean_coord = "".join(ch for ch in settings.COORDINATOR_PHONE if ch.isdigit())
                if clean_chat and clean_coord and not (clean_chat.endswith(clean_coord[-9:]) or clean_coord.endswith(clean_chat[-9:])):
                    # Outgoing message sent by Ryan to someone else, not self-test
                    return

            await task_engine.process_volunteer_message(
                sender_phone=sender_phone,
                sender_name=sender_name,
                text=text
            )

green_poller = GreenApiPoller()
