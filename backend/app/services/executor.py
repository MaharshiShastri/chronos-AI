import asyncio
import time
from app.services.optimizer import TimeOptimizer
from sqlalchemy.orm import Session
import logging
from app.models import models

logger = logging.getLogger(__name__)

def perform_task():
    pass

async def run_mission_retry(step_data, retries=3):
    for attempt in range(retries):
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(perform_task, step_data),
                timout=30.0
            )

            if result:
                return result
        except asyncio.TimeoutError:
            logger.warning(f"Attempt: {attempt+1} timed out. Retrying...")
        
    return {"success": False, "error": "MAX_RETRIES_REACHED"}

async def run_mission_stream(mission_id: int, total_budget: int, db:Session):
    #Simulating what an agent might do here with time-constraints and dynamic adjustments
    #executed_steps = []
    task =  db.query(models.Tasks).filter(models.Tasks.id == mission_id).first()
    steps = db.query(models.TaskStep).filter(models.TaskStep.task_id == mission_id).order_by(models.TaskStep.order.asc()).all()
                                                                                             
    start_time = time.time()
    for i, step in enumerate(steps):
        step_start_marker = time.time()
        step.status = "started"
        db.commit()

        yield{
            "event": "STEP_STARTED",
            "index": i,
            "step_id": step.get("step_id"),
            "time_remaining": max(0, abs(total_budget - step_start_marker))
        }

        allocated_time = step["time_allocated"]
        artifact = f"Generated content for: {step['step']}" #The actual task would done via this line
        step.artifact_content = artifact
        step.status = "awaiting_approval"

        await asyncio.sleep(min(allocated_time, 2))

        actual_duration = time.time() - step_start_marker
        step.actual_duration = actual_duration
        drift = actual_duration - allocated_time

        yield{
            "event": "REQUIRE_APPROVAL",
            "index": i,
            "step_id": step.backend_step_id,
            'content': {"artifact": artifact or "Testing", "time_needed": actual_duration, "drift": drift if drift > 0 else 0},
            "instructions": "Please approve or provide feedback to refine this step."
        }
        
        approved = False
        while not approved:
            await asyncio.sleep(1)
            db.refresh(step)
            if step.status.lower() in ["completed", "refined"]:
                approved = True

        if(drift > 0):
            steps = TimeOptimizer.calculate_drift_correction(steps, i, drift)

        yield{
            "event": "STEP_COMPLETED",
            "index": i,
            "actual_duration": round(actual_duration, 2),
            "updated_steps": steps
        }

    task.status = "completed"
    db.commit()
    yield{"event":"MISSION_COMPLETED", "mission_id": mission_id}