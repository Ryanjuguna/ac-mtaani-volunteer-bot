from fastapi import APIRouter, Request, Response
from typing import Dict, Any
from app.task_engine import task_engine
from app.parser import parser

router = APIRouter(prefix="/webhook", tags=["Webhook"])

@router.post("")
async def receive_whatsapp_webhook(request: Request):
    """
    Receives incoming webhook payloads from Green API or test harnesses.
    Handles both Group chats (task assignments) and Private DMs (volunteer replies).
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    print(f"[Incoming Webhook Event]: {data}")

    # 1. Parse Green API payload structure
    type_webhook = data.get("typeWebhook")
    
    if type_webhook in ["incomingMessageReceived", "outgoingMessageReceived"]:
        if data.get("sendByApi"):
            return {"status": "ignored", "reason": "Bot's own API message"}

        sender_data = data.get("senderData", {})
        message_data = data.get("messageData", {})
        
        chat_id = data.get("chatId") or sender_data.get("chatId", "")
        sender_name = data.get("senderName") or sender_data.get("senderName", "WhatsApp User")
        sender_phone = (
            data.get("senderId", "").replace("@c.us", "").replace("@g.us", "") or
            sender_data.get("sender", "").replace("@c.us", "").replace("@g.us", "") or
            chat_id.replace("@c.us", "").replace("@g.us", "")
        )
        
        text = (
            data.get("textMessage") or
            message_data.get("textMessageData", {}).get("textMessage") or
            message_data.get("extendedTextMessageData", {}).get("text") or
            ""
        )

        has_task = parser.has_trigger(text)

        if has_task:
            result = await task_engine.process_group_message(
                sender_name=sender_name,
                sender_phone=sender_phone,
                text=text,
                chat_id=chat_id
            )
            return {"status": "success", "type": "assignment", "result": result}
        else:
            result = await task_engine.process_volunteer_message(
                sender_phone=sender_phone,
                sender_name=sender_name,
                text=text
            )
            return {"status": "success", "type": "volunteer_reply", "result": result}

    # 2. Support direct simplified test payload
    elif "text" in data:
        text = data.get("text", "")
        sender_name = data.get("sender_name", "Coordinator")
        sender_phone = data.get("sender_phone", "+254700000000")
        is_group = data.get("is_group", True)
        chat_id = data.get("chat_id", "mtaani_tech_group@g.us")

        if is_group:
            result = await task_engine.process_group_message(
                sender_name=sender_name,
                sender_phone=sender_phone,
                text=text,
                chat_id=chat_id
            )
        else:
            result = await task_engine.process_volunteer_message(
                sender_phone=sender_phone,
                sender_name=sender_name,
                text=text
            )
        return {"status": "success", "type": "custom", "result": result}

    return {"status": "ignored", "reason": "Unsupported webhook format or event"}
