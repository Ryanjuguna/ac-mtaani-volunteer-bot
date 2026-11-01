import json
import os
import difflib
from typing import List, Optional, Tuple
from app.models import Volunteer
from app.config import settings

class VolunteerRegistry:
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or settings.VOLUNTEERS_FILE
        self.volunteers: List[Volunteer] = []
        self.load()

    def load(self):
        target = self.filepath
        if not os.path.exists(target):
            example_file = os.path.join(os.path.dirname(target), "volunteers.example.json")
            if os.path.exists(example_file):
                target = example_file

        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.volunteers = [Volunteer(**item) for item in data]
        else:
            self.volunteers = []

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([v.model_dump() for v in self.volunteers], f, indent=2)

    def get_all(self) -> List[Volunteer]:
        return self.volunteers

    def get_by_id(self, volunteer_id: str) -> Optional[Volunteer]:
        for v in self.volunteers:
            if v.id == volunteer_id:
                return v
        return None

    def get_by_phone(self, phone: str) -> Optional[Volunteer]:
        # Normalize phone (remove +, spaces, hyphens)
        clean_phone = "".join(ch for ch in phone if ch.isdigit())
        for v in self.volunteers:
            v_phone = "".join(ch for ch in v.phone if ch.isdigit())
            if v_phone.endswith(clean_phone[-9:]) or clean_phone.endswith(v_phone[-9:]):
                return v
        return None

    def resolve(self, query: str) -> Tuple[Optional[Volunteer], float]:
        """
        Fuzzy resolves an extracted mention or name string to a registered volunteer.
        Returns (Volunteer, confidence_score between 0.0 and 1.0)
        """
        if not query or not self.volunteers:
            return None, 0.0

        clean_query = query.strip().lstrip("@").strip().lower()
        if not clean_query:
            return None, 0.0

        # 1. Exact match on handle
        for v in self.volunteers:
            if v.handle.lower() == clean_query:
                return v, 1.0

        # 2. Exact match on full name
        for v in self.volunteers:
            if v.name.lower() == clean_query:
                return v, 1.0

        # 3. Handle or first name in query
        for v in self.volunteers:
            first_name = v.name.split()[0].lower()
            if first_name == clean_query or v.handle.lower() in clean_query:
                return v, 0.95

        # 4. Partial substring in full name
        for v in self.volunteers:
            if clean_query in v.name.lower():
                return v, 0.90

        # 5. Fuzzy matching using difflib
        best_match = None
        best_score = 0.0

        for v in self.volunteers:
            score_handle = difflib.SequenceMatcher(None, clean_query, v.handle.lower()).ratio()
            score_first = difflib.SequenceMatcher(None, clean_query, v.name.split()[0].lower()).ratio()
            score_full = difflib.SequenceMatcher(None, clean_query, v.name.lower()).ratio()
            score = max(score_handle, score_first, score_full)

            if score > best_score:
                best_score = score
                best_match = v

        if best_score >= 0.65:
            return best_match, round(best_score, 2)

        return None, 0.0

    def add_volunteer(self, volunteer: Volunteer) -> Volunteer:
        self.volunteers.append(volunteer)
        self.save()
        return volunteer

registry = VolunteerRegistry()
