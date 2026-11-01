import os
from typing import Optional, Dict, Any, List
from app.models import Task
from app.config import settings

class GoogleSheetsService:
    def __init__(self):
        self.enabled = settings.ENABLE_SHEETS_SYNC
        self.sheet_id = settings.GOOGLE_SHEET_ID
        self.creds_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE
        self.client = None
        self.sheet = None
        self.mock_sheet_rows: List[Dict[str, Any]] = []
        self._init_client()

    def _init_client(self):
        if self.enabled and os.path.exists(self.creds_file) and self.sheet_id:
            try:
                import gspread
                self.client = gspread.service_account(filename=self.creds_file)
                self.sheet = self.client.open_by_key(self.sheet_id).sheet1
                print("[Google Sheets] Successfully connected to live Google Sheet!")
            except Exception as e:
                print(f"[Google Sheets Warning] Connection failed: {e}. Running in local mirror mode.")

    def sync_task(self, task: Task) -> bool:
        """
        Appends or updates a task in the Google Sheet dashboard.
        """
        row_data = {
            "Task ID": task.id,
            "Created At": task.created_at[:16].replace("T", " "),
            "Task Description": task.title,
            "Assignee Name": task.assignee_name,
            "Phone Number": task.assignee_phone,
            "Deadline": task.deadline_text or (task.deadline_iso[:16].replace("T", " ") if task.deadline_iso else "N/A"),
            "Priority": task.priority.value,
            "Category": task.category,
            "Status": task.status.value,
            "Volunteer Notes": task.volunteer_notes or "",
            "Last Updated": task.last_updated[:16].replace("T", " ")
        }

        # Update in-memory mirror
        existing_idx = next((i for i, r in enumerate(self.mock_sheet_rows) if r["Task ID"] == task.id), None)
        if existing_idx is not None:
            self.mock_sheet_rows[existing_idx] = row_data
        else:
            self.mock_sheet_rows.append(row_data)

        # Sync to live Google Sheets if active
        if self.sheet:
            try:
                # Search for existing Task ID row
                cell = self.sheet.find(task.id)
                values = list(row_data.values())
                if cell:
                    self.sheet.update(range_name=f"A{cell.row}:K{cell.row}", values=[values])
                else:
                    self.sheet.append_row(values)
                return True
            except Exception as e:
                print(f"[Google Sheets Sync Error]: {e}")
                return False

        return True

    def get_dashboard_rows(self) -> List[Dict[str, Any]]:
        return self.mock_sheet_rows

sheets_service = GoogleSheetsService()
