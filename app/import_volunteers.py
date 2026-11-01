import os
import csv
import json
from typing import List
from app.models import Volunteer
from app.registry import registry

def import_volunteers_from_csv(csv_path: str) -> List[Volunteer]:
    """
    Imports volunteers from a standard CSV file with columns:
    Name, Phone, Email, Department (or Pillar)
    """
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return []

    imported = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        idx = len(registry.get_all()) + 1
        for row in reader:
            # Map column names flexibly
            name = row.get("Name") or row.get("Full Name") or row.get("Full Names") or ""
            phone = row.get("Phone") or row.get("Phone Number") or row.get("Contact") or row.get("WhatsApp") or ""
            email = row.get("Email") or row.get("Email Address") or ""
            dept = row.get("Department") or row.get("Pillar") or row.get("Program") or "General Support"

            if not name.strip() or not phone.strip():
                continue

            # First name as default handle
            handle = name.strip().split()[0].replace("@", "")
            
            vol = Volunteer(
                id=f"VOL-{idx:03d}",
                name=name.strip(),
                handle=handle,
                phone=phone.strip(),
                email=email.strip() if email else None,
                pillar=dept.strip(),
                status="active"
            )
            registry.add_volunteer(vol)
            imported.append(vol)
            idx += 1

    print(f"Successfully imported {len(imported)} volunteers into the registry!")
    return imported

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        import_volunteers_from_csv(sys.argv[1])
    else:
        print("Usage: python -m app.import_volunteers <path_to_csv>")
