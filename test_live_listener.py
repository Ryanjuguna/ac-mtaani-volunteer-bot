import asyncio
import httpx
from app.config import settings

async def listen():
    instance_id = settings.GREEN_API_INSTANCE_ID
    token = settings.GREEN_API_TOKEN
    
    print("=" * 65)
    print("  GREEN API LIVE DIAGNOSTIC LISTENER")
    print(f"  Instance ID: {instance_id}")
    print(f"  Status: Polling Green API queue in real-time...")
    print("  👉 Send any message on WhatsApp from your phone now!")
    print("  (Press Ctrl+C to stop)")
    print("=" * 65)

    receive_url = f"https://api.green-api.com/waInstance{instance_id}/receiveNotification/{token}"
    delete_url = f"https://api.green-api.com/waInstance{instance_id}/deleteNotification/{token}"

    async with httpx.AsyncClient(timeout=25.0) as client:
        while True:
            try:
                resp = await client.get(receive_url)
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    receipt_id = data.get("receiptId")
                    body = data.get("body", {})
                    type_webhook = body.get("typeWebhook")
                    
                    sender_data = body.get("senderData", {})
                    msg_data = body.get("messageData", {})
                    
                    chat = sender_data.get("chatId", "Unknown")
                    sender = sender_data.get("senderName") or sender_data.get("sender", "Unknown")
                    
                    text = ""
                    if "textMessageData" in msg_data:
                        text = msg_data["textMessageData"].get("textMessage", "")
                    elif "extendedTextMessageData" in msg_data:
                        text = msg_data["extendedTextMessageData"].get("text", "")
                    
                    safe_text = text.encode("ascii", errors="replace").decode("ascii")
                    print(f"\n[EVENT: {type_webhook}]")
                    print(f"Chat: {chat}")
                    print(f"From: {sender}")
                    print(f"Message: {safe_text}")
                    
                    # Acknowledge / Delete from queue
                    if receipt_id:
                        await client.delete(f"{delete_url}/{receipt_id}")

                await asyncio.sleep(1.0)
            except KeyboardInterrupt:
                print("\nStopping listener...")
                break
            except Exception as e:
                print(f"[Error]: {e}")
                await asyncio.sleep(2.0)

if __name__ == "__main__":
    asyncio.run(listen())
