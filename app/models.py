from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DM_SENT = "DM_SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    OVERDUE = "OVERDUE"

class TaskPriority(str, Enum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class Volunteer(BaseModel):
    id: str
    name: str
    handle: str
    phone: str
    email: Optional[str] = None
    pillar: Optional[str] = None
    status: str = "active"

class ParsedTaskResult(BaseModel):
    is_task: bool = True
    assignee_mention: str = Field(description="The name or tag of the person assigned, e.g. 'Faith' or '@Faith'")
    task_description: str = Field(description="Actionable, clear summary of the task")
    deadline_raw: str = Field(description="Original time or deadline mentioned in text, e.g. 'tomorrow 3pm', 'Friday'")
    deadline_iso: Optional[str] = Field(default=None, description="ISO 8601 formatted datetime if resolvable")
    priority: TaskPriority = TaskPriority.MEDIUM
    category: str = Field(default="GENERAL", description="Domain category e.g. MAKERSPACE, GAMING, VR, TECH, OUTREACH")
    confidence: float = 1.0

class Task(BaseModel):
    id: str
    title: str
    assignee_id: str
    assignee_name: str
    assignee_phone: str
    assigned_by: str = "Coordinator"
    created_at: str
    deadline_iso: Optional[str] = None
    deadline_text: str = ""
    status: TaskStatus = TaskStatus.DM_SENT
    priority: TaskPriority = TaskPriority.MEDIUM
    category: str = "GENERAL"
    raw_message: str = ""
    volunteer_notes: Optional[str] = None
    last_updated: str

class MessageWebhookPayload(BaseModel):
    chat_id: str
    sender_name: str
    sender_phone: str
    text: str
    is_group: bool = True
    timestamp: Optional[int] = None
