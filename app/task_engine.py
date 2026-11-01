import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from app.models import Task, TaskStatus, TaskPriority, ParsedTaskResult
from app.parser import parser
from app.registry import registry
from app.storage import storage
from app.sheets_service import sheets_service
from app.whatsapp_service import whatsapp_service
from app.config import settings

class TaskEngine:
    def __init__(self):
        self.task_counter = 1000

    def _generate_task_id(self) -> str:
        tasks = storage.get_all_tasks()
        if tasks:
            # Extract numeric suffix from existing tasks
            nums = []
            for t in tasks:
                parts = t.id.split("-")
                if len(parts) == 2 and parts[1].isdigit():
                    nums.append(int(parts[1]))
            if nums:
                return f"TSK-{max(nums) + 1}"
        return f"TSK-1001"

    async def process_group_message(
        self,
        sender_name: str,
        sender_phone: str,
        text: str,
        chat_id: str
    ) -> Dict[str, Any]:
        """
        Processes an incoming group chat message.
        If message contains @task, extracts task details and assigns to volunteer.
        """
        if not parser.has_trigger(text):
            return {
                "is_task": False,
                "message": "No @task trigger detected. Ignored."
            }

        # 1. Parse text using Gemini / heuristic parser
        now = datetime.now()
        parsed: Optional[ParsedTaskResult] = parser.parse(text, reference_time=now)
        if not parsed or not parsed.is_task:
            return {
                "is_task": False,
                "message": "Failed to extract task content from message."
            }

        # 2. Fuzzy resolve assignee
        volunteer, confidence = registry.resolve(parsed.assignee_mention)
        if not volunteer:
            # NEVER spam the group with error receipts. Log internally.
            all_handles = ", ".join([f"@{v.handle}" for v in registry.get_all()[:5]])
            print(f"[TaskEngine] Assignee '{parsed.assignee_mention}' could not be resolved. Skipping group receipt.")
            
            # If tested in private DM / self-chat, inform coordinator directly:
            if not chat_id.endswith("@g.us"):
                feedback = f"⚠️ Could not match '{parsed.assignee_mention}' to any registered volunteer. Registered handles include: {all_handles}"
                await whatsapp_service.send_direct_message(sender_phone, feedback)
                
            return {
                "is_task": True,
                "status": "UNRESOLVED_ASSIGNEE",
                "extracted": parsed.model_dump(),
                "error": f"Volunteer '{parsed.assignee_mention}' not found"
            }

        # 3. Create Task Record
        task_id = self._generate_task_id()
        task = Task(
            id=task_id,
            title=parsed.task_description,
            assignee_id=volunteer.id,
            assignee_name=volunteer.name,
            assignee_phone=volunteer.phone,
            assigned_by=sender_name or "Coordinator",
            created_at=now.isoformat(),
            deadline_iso=parsed.deadline_iso,
            deadline_text=parsed.deadline_raw,
            status=TaskStatus.DM_SENT,
            priority=parsed.priority,
            category=parsed.category,
            raw_message=text,
            last_updated=now.isoformat()
        )

        # 4. Save to SQLite and sync to Google Sheets
        storage.create_task(task)
        sheets_service.sync_task(task)

        # 5. Send Private WhatsApp DM to the Volunteer
        dm_content = (
            f"👋 *Hi {volunteer.name.split()[0]}!*\n"
            f"A new task has been assigned to you by the Coordinator:\n\n"
            f"📋 *Task:* {task.title}\n"
            f"⏰ *Deadline:* {task.deadline_text}\n"
            f"🏷️ *Category:* {task.category} | *Priority:* {task.priority.value}\n\n"
            f"Please reply with:\n"
            f"• *1* to *Accept*\n"
            f"• *2* if *Unavailable*\n"
            f"• Type *Done* once finished!"
        )
        await whatsapp_service.send_direct_message(volunteer.phone, dm_content)

        # 6. Send Terse Confirmation Receipt to Group Chat (only if assigned in a group)
        if chat_id.endswith("@g.us"):
            group_receipt = f"📌 *Task #{task_id}* logged for *@{volunteer.handle}*. Full details and deadline sent via DM."
            await whatsapp_service.send_group_receipt(chat_id, group_receipt)

        return {
            "is_task": True,
            "status": "ASSIGNED",
            "task": task.model_dump(),
            "volunteer": volunteer.model_dump(),
            "extracted": parsed.model_dump()
        }

    async def process_volunteer_message(
        self,
        sender_phone: str,
        sender_name: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Handles incoming 1-on-1 private WhatsApp replies from volunteers.
        Supports 1-touch numeric actions (1: Accept, 2: Decline, 'Done': Completed).
        """
        clean_text = text.strip().lower()
        active_task = storage.get_latest_task_for_volunteer(sender_phone)
        volunteer = registry.get_by_phone(sender_phone)
        first_name = volunteer.name.split()[0] if volunteer else sender_name

        if not active_task:
            # Only reply if user explicitly typed a command, number, or keyword
            keywords = ["1", "2", "done", "task", "tasks", "status", "help", "work", "volunteer"]
            if any(k in clean_text for k in keywords):
                reply = (
                    f"Hi {first_name}! You currently have no pending tasks assigned at American Corner Mtaani. "
                    "When the coordinator assigns a new task, you'll receive the details right here!"
                )
                await whatsapp_service.send_direct_message(sender_phone, reply)
                return {"status": "NO_ACTIVE_TASK", "reply": reply}
            else:
                # Silently ignore casual messages to protect user's personal chat privacy
                return {"status": "NO_ACTIVE_TASK_IGNORED"}

        # 1. Volunteer Accepts
        if clean_text in ["1", "accept", "accepted", "sure", "i will do it", "on it"]:
            updated = storage.update_task_status(active_task.id, TaskStatus.ACKNOWLEDGED)
            if updated:
                sheets_service.sync_task(updated)
            reply = f"✅ Awesome, {first_name}! Task *#{active_task.id}* is acknowledged. We appreciate your dedication to the Space!"
            await whatsapp_service.send_direct_message(sender_phone, reply)
            return {"status": "ACKNOWLEDGED", "task": updated.model_dump() if updated else None}

        # 2. Volunteer Declines
        elif clean_text in ["2", "decline", "unavailable", "can't", "cannot"]:
            updated = storage.update_task_status(active_task.id, TaskStatus.DECLINED, notes="Volunteer reported unavailable")
            if updated:
                sheets_service.sync_task(updated)
            reply = f"Understood, {first_name}. I have marked task *#{active_task.id}* as unavailable so the coordinator can reassign it."
            await whatsapp_service.send_direct_message(sender_phone, reply)
            return {"status": "DECLINED", "task": updated.model_dump() if updated else None}

        # 3. Volunteer Marks Completed
        elif any(w in clean_text for w in ["done", "complete", "finished", "all done", "resolved"]):
            updated = storage.update_task_status(active_task.id, TaskStatus.COMPLETED, notes=f"Completed by volunteer: {text}")
            if updated:
                sheets_service.sync_task(updated)
            reply = f"🎉 Great job, {first_name}! Task *#{active_task.id}* is marked as *COMPLETED*. Thank you for empowering our community!"
            await whatsapp_service.send_direct_message(sender_phone, reply)
            return {"status": "COMPLETED", "task": updated.model_dump() if updated else None}

        # 4. General Response / Progress update
        else:
            updated = storage.update_task_status(active_task.id, TaskStatus.IN_PROGRESS, notes=f"Progress update: {text}")
            if updated:
                sheets_service.sync_task(updated)
            reply = f"Got it, {first_name}! Progress recorded for *#{active_task.id}* ('{active_task.title}'). Remember to reply *Done* when completed!"
            await whatsapp_service.send_direct_message(sender_phone, reply)
            return {"status": "IN_PROGRESS", "task": updated.model_dump() if updated else None}

task_engine = TaskEngine()
