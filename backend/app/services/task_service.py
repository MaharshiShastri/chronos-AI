import re
import json
import uuid
from sqlalchemy.orm import Session
from app.models import models

def clean_and_parse_plan(raw_text: str):
    try:
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        if match:
            clean_json = match.group(0).replace("}{", "},{")
            return json.loads(clean_json)
        
        # Fallback for individual objects
        found_objects = re.findall(r'\{[^{}]*\}', raw_text, re.DOTALL)
        return [json.loads(obj) for obj in found_objects]
    except Exception:
        return []

def create_mission_and_steps(db: Session, user_id: int, task_title: str, budget: int, raw_steps: list):
    # Create Main Mission
    mission = models.Tasks(user_id=user_id, title=task_title[:50], total_time=budget, status="pending")
    db.add(mission)
    db.commit()
    db.refresh(mission)

    # Save Steps
    enriched_steps = []
    for idx, s in enumerate(raw_steps):
        step_entry = models.TaskStep(
            task_id=mission.id,
            backend_step_id=f"STP-{uuid.uuid4().hex[:6].upper()}",
            description=s.get("step") or s.get("description", "No description"),
            time_allocated=s.get("time_allocated", 60),
            order=idx
        )
        db.add(step_entry)
        enriched_steps.append({
            "step_id": step_entry.backend_step_id,
            "step": step_entry.description,
            "time_allocated": step_entry.time_allocated
        })
    
    db.commit()
    return mission.id, enriched_steps