import os
import re
import json
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.models import ParsedTaskResult, TaskPriority
from app.config import settings

class TaskParser:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._init_gemini()

    def _init_gemini(self):
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Failed to initialize Google GenAI client: {e}")

    def has_trigger(self, text: str) -> bool:
        """Check if message explicitly contains @task or #task (never match bare word 'task')."""
        if not text:
            return False
        # Strictly require @task or #task - bare word 'task' in conversation will NOT trigger
        pattern = r"(?:^|\s)(?:@task|#task)(?:\b|\s|$)"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def parse(self, text: str, reference_time: Optional[datetime] = None) -> Optional[ParsedTaskResult]:
        """
        Parses a coordinator message. If GEMINI_API_KEY is available, uses Gemini 2.5.
        Otherwise falls back to high-accuracy local heuristic parser.
        """
        if not self.has_trigger(text):
            return None

        ref_time = reference_time or datetime.now()

        # Try Gemini first if client is available
        if self.client:
            try:
                return self._parse_with_gemini(text, ref_time)
            except Exception as e:
                print(f"[Parser] Gemini API call error: {e}. Falling back to heuristic parser.")

        # Fallback heuristic parser
        return self._parse_heuristic(text, ref_time)

    def _parse_with_gemini(self, text: str, ref_time: datetime) -> ParsedTaskResult:
        from google.genai import types

        prompt = f"""You are the Solutions Architect AI for American Corner Mtaani (a U.S. Embassy American Space community hub in Nairobi).
The Coordinator is assigning a task in the WhatsApp group chat.
Current local timestamp: {ref_time.strftime('%Y-%m-%d %H:%M:%S (%A)')} (Timezone: East Africa Time UTC+3).

Analyze the coordinator's message:
\"\"\"{text}\"\"\"

Extract the assignment into structured JSON:
- assignee_mention: Name or @tag of the volunteer being addressed (e.g., 'Faith', '@Brian'). Remove leading '@' if present.
- task_description: Concise, clear, professional action item (e.g. 'Inspect Makerbot 3D printer wiring and run test print').
- deadline_raw: The deadline phrase as stated in text (e.g. 'tomorrow 3pm', 'this Saturday at 10am').
- deadline_iso: Calculated ISO 8601 datetime string based on the current timestamp. If no time is specified, default to 17:00 (5:00 PM).
- priority: 'URGENT', 'HIGH', 'MEDIUM', or 'LOW'.
- category: Domain category like 'MAKERSPACE', 'GAMING', 'VR', 'TECH_PROGRAM', 'COMMUNICATIONS', or 'GENERAL'.
- is_task: true if an actual task is being assigned.
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ParsedTaskResult,
                temperature=0.1
            ),
        )

        data = json.loads(response.text)
        return ParsedTaskResult(**data)

    def _parse_heuristic(self, text: str, ref_time: datetime) -> ParsedTaskResult:
        """
        Resilient heuristic extractor when Gemini API key is not yet configured.
        Dissects the message into assignee, task, and deadline.
        """
        raw = text.strip()
        
        # 1. Remove the trigger tag strictly (@task or #task)
        cleaned = re.sub(r"(?:^|\s)(?:@task|#task)(?:\b|\s|$)", " ", raw, flags=re.IGNORECASE).strip()

        # 2. Extract potential mentions (@Name)
        mention_match = re.search(r"@([A-Za-z0-9_\-\.]+)", cleaned)
        assignee = ""
        if mention_match:
            cand = mention_match.group(1)
            if cand.lower() not in ["task", "todo"]:
                assignee = cand
                cleaned = cleaned.replace(f"@{cand}", " ").strip()
        else:
            # If no @mention, check if the first word is a registered volunteer name
            words = cleaned.split()
            if words:
                from app.registry import registry
                cand_name = words[0].strip(".,!?:")
                vol, conf = registry.resolve(cand_name)
                if vol and conf >= 0.7:
                    assignee = cand_name
                    cleaned = " ".join(words[1:]).strip()

        # If no valid assignee could be identified, this is NOT an actionable task
        if not assignee:
            return ParsedTaskResult(
                is_task=False,
                assignee_mention="",
                task_description="",
                deadline_raw="",
                deadline_iso=None,
                priority=TaskPriority.MEDIUM,
                category="GENERAL",
                confidence=0.0
            )

        # 3. Detect deadline patterns
        deadline_raw = "Next session"
        deadline_iso = None
        priority = TaskPriority.MEDIUM

        # Check for urgent keywords
        if any(w in raw.lower() for w in ["urgent", "asap", "immediately", "quick"]):
            priority = TaskPriority.URGENT

        # Regex for deadline phrases
        deadline_patterns = [
            (r"\bby\s+(tomorrow\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\w+\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|tomorrow|today|friday|saturday|sunday|monday|tuesday|wednesday|thursday)", 1),
            (r"\bbefore\s+([\w\s\d:]+(?:am|pm)?)", 1),
            (r"\bdue\s+([\w\s\d:]+(?:am|pm)?)", 1),
            (r"\bat\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", 1),
        ]

        for pat, group_idx in deadline_patterns:
            m = re.search(pat, cleaned, re.IGNORECASE)
            if m:
                deadline_raw = m.group(group_idx).strip()
                # Remove deadline phrase from task description
                cleaned = cleaned[:m.start()] + cleaned[m.end():]
                break

        # Calculate deadline_iso approximation
        dl_lower = deadline_raw.lower()
        if "tomorrow" in dl_lower:
            target_date = ref_time + timedelta(days=1)
            deadline_iso = target_date.replace(hour=17, minute=0, second=0).isoformat()
        elif "today" in dl_lower:
            target_date = ref_time
            deadline_iso = target_date.replace(hour=17, minute=0, second=0).isoformat()
        else:
            target_date = ref_time + timedelta(days=2)
            deadline_iso = target_date.replace(hour=17, minute=0, second=0).isoformat()

        # 4. Clean task description
        # Clean filler words: "please", "can you", "help", "could you"
        task_desc = re.sub(r"^(please|can you|could you|kindly|help to|help)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        task_desc = re.sub(r"\s+", " ", task_desc).strip(",;.- ")

        if not task_desc:
            task_desc = "Coordinate assigned volunteer activity"

        # Determine category
        desc_lower = task_desc.lower()
        category = "GENERAL"
        if any(w in desc_lower for w in ["3d", "printer", "makerbot", "wiring", "filament"]):
            category = "MAKERSPACE"
        elif any(w in desc_lower for w in ["chess", "game", "barbah", "esports"]):
            category = "GAMING"
        elif any(w in desc_lower for w in ["vr", "headset", "oculus", "meta"]):
            category = "VR"
        elif any(w in desc_lower for w in ["poster", "social", "flyer", "instagram", "facebook"]):
            category = "COMMUNICATIONS"

        return ParsedTaskResult(
            is_task=True,
            assignee_mention=assignee,
            task_description=task_desc.capitalize(),
            deadline_raw=deadline_raw,
            deadline_iso=deadline_iso,
            priority=priority,
            category=category,
            confidence=0.85
        )

parser = TaskParser()
