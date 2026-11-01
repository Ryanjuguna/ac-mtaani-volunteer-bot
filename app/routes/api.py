from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.models import Volunteer, Task, TaskStatus
from app.registry import registry
from app.storage import storage
from app.sheets_service import sheets_service
from app.whatsapp_service import whatsapp_service
from app.task_engine import task_engine

router = APIRouter(prefix="/api", tags=["API"])

class CoordinatorMessageRequest(BaseModel):
    message: str
    sender_name: str = "Coordinator (Ryan)"
    sender_phone: str = "+254700000000"
    chat_id: str = "mtaani_volunteers_group@g.us"

class VolunteerReplyRequest(BaseModel):
    phone: str
    message: str
    sender_name: Optional[str] = None

@router.get("/tasks", response_model=List[Task])
async def list_tasks():
    return storage.get_all_tasks()

@router.get("/volunteers", response_model=List[Volunteer])
async def list_volunteers():
    return registry.get_all()

@router.post("/volunteers", response_model=Volunteer)
async def create_volunteer(vol: Volunteer):
    return registry.add_volunteer(vol)

@router.get("/dashboard")
async def get_dashboard_data():
    tasks = storage.get_all_tasks()
    volunteers = registry.get_all()
    
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    in_progress = sum(1 for t in tasks if t.status in [TaskStatus.ACKNOWLEDGED, TaskStatus.IN_PROGRESS])
    pending_or_sent = sum(1 for t in tasks if t.status in [TaskStatus.PENDING, TaskStatus.DM_SENT])
    declined_tasks = sum(1 for t in tasks if t.status == TaskStatus.DECLINED)

    return {
        "stats": {
            "total_tasks": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_progress,
            "pending_or_sent": pending_or_sent,
            "declined": declined_tasks,
            "total_volunteers": len(volunteers)
        },
        "tasks": [t.model_dump() for t in tasks],
        "volunteers": [v.model_dump() for v in volunteers],
        "sheets_mirror": sheets_service.get_dashboard_rows(),
        "recent_outbox": whatsapp_service.get_recent_outbox()
    }

@router.post("/simulate/coordinator")
async def simulate_coordinator_message(req: CoordinatorMessageRequest):
    """
    Simulates the coordinator sending a message into the WhatsApp Group.
    """
    result = await task_engine.process_group_message(
        sender_name=req.sender_name,
        sender_phone=req.sender_phone,
        text=req.message,
        chat_id=req.chat_id
    )
    return {
        "status": "success",
        "result": result,
        "recent_outbox": whatsapp_service.get_recent_outbox()
    }

@router.post("/simulate/volunteer")
async def simulate_volunteer_reply(req: VolunteerReplyRequest):
    """
    Simulates a volunteer replying to the bot's private WhatsApp message.
    """
    result = await task_engine.process_volunteer_message(
        sender_phone=req.phone,
        sender_name=req.sender_name or "Volunteer",
        text=req.message
    )
    return {
        "status": "success",
        "result": result,
        "recent_outbox": whatsapp_service.get_recent_outbox()
    }
