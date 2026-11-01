import os
import sqlite3
from typing import List, Optional
from datetime import datetime
from app.models import Task, TaskStatus, TaskPriority
from app.config import settings

class TaskStorage:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    assignee_id TEXT NOT NULL,
                    assignee_name TEXT NOT NULL,
                    assignee_phone TEXT NOT NULL,
                    assigned_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    deadline_iso TEXT,
                    deadline_text TEXT,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    category TEXT NOT NULL,
                    raw_message TEXT,
                    volunteer_notes TEXT,
                    last_updated TEXT NOT NULL
                )
            """)
            conn.commit()

    def create_task(self, task: Task) -> Task:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks (
                    id, title, assignee_id, assignee_name, assignee_phone,
                    assigned_by, created_at, deadline_iso, deadline_text,
                    status, priority, category, raw_message, volunteer_notes, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.title, task.assignee_id, task.assignee_name, task.assignee_phone,
                task.assigned_by, task.created_at, task.deadline_iso, task.deadline_text,
                task.status.value, task.priority.value, task.category, task.raw_message,
                task.volunteer_notes, task.last_updated
            ))
            conn.commit()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_task(row)
        return None

    def get_latest_task_for_volunteer(self, phone: str) -> Optional[Task]:
        clean_phone = "".join(ch for ch in phone if ch.isdigit())
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE status NOT IN ('COMPLETED', 'DECLINED') ORDER BY created_at DESC"
            )
            for row in cursor.fetchall():
                row_phone = "".join(ch for ch in row["assignee_phone"] if ch.isdigit())
                if row_phone.endswith(clean_phone[-9:]) or clean_phone.endswith(row_phone[-9:]):
                    return self._row_to_task(row)
        return None

    def get_all_tasks(self) -> List[Task]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            return [self._row_to_task(row) for row in cursor.fetchall()]

    def update_task_status(self, task_id: str, new_status: TaskStatus, notes: Optional[str] = None) -> Optional[Task]:
        task = self.get_task(task_id)
        if not task:
            return None
        
        task.status = new_status
        task.last_updated = datetime.now().isoformat()
        if notes:
            task.volunteer_notes = notes

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE tasks
                SET status = ?, last_updated = ?, volunteer_notes = ?
                WHERE id = ?
            """, (task.status.value, task.last_updated, task.volunteer_notes, task.id))
            conn.commit()

        return task

    def _row_to_task(self, row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            assignee_id=row["assignee_id"],
            assignee_name=row["assignee_name"],
            assignee_phone=row["assignee_phone"],
            assigned_by=row["assigned_by"],
            created_at=row["created_at"],
            deadline_iso=row["deadline_iso"],
            deadline_text=row["deadline_text"],
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            category=row["category"],
            raw_message=row["raw_message"] or "",
            volunteer_notes=row["volunteer_notes"],
            last_updated=row["last_updated"]
        )

storage = TaskStorage()
