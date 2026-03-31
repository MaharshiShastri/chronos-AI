import asyncio
import time
from optimizer import TimeOptimizer

pending_approvals = {}
async def run_mission_stream(mission_id, steps, total_budget):
    #Simulating what an agent might do here with time-constraints and dynamic adjustments

    start_time = time.time()
    elapsed_time = 0
    for i, step in enumerate(steps):
        step_start_marker = time.time()

        yield{
            "event": "STEP_STARTED",
            "index": i,
            "step_id": step.get("step_id"),
            "time_remaining": max(0, total_budget - elapsed_time)
        }

        allocated_time = step["time_allocated"]
        artifact = f"Generated content for: {step["step"]}"
        await asyncio.sleep(min(allocated_time, 2))

        approval_event = asyncio.Event()
        actual_duration = time.time() - step_start_marker
        drift = actual_duration - allocated_time

        pending_approvals[mission_id] = {
            "event": approval_event,
            "data": artifact or "Testing",
            "status": "pending"
        }

        yield{
            "event": "REQUIRE_APPROVAL",
            "index": i,
            'content': {"artifact": artifact or "Testing", "time_needed": actual_duration, "drift": drift if drift > 0 else 0},
            "instructions": "Please approve or provide feedback to refine this step."
        }
        await approval_event.wait()

        user_response = pending_approvals[mission_id]
        if user_response["status"] == "refined":
            artifact = user_response["data"]
            yield {"event": "STEP_REFINED", "index": i, "new_content": artifact}

        if(drift > 0):
            steps = TimeOptimizer.calculate_drift_correction(steps, i, drift)

        yield{
            "event": "STEP_COMPLETED",
            "index": i,
            "actual_duration": round(actual_duration, 2),
            "updated_steps": steps
        }
        del pending_approvals[mission_id]
        elapsed_time = time.time() - start_time

    yield{"event":"MISSION_COMPLETED", "mission_id": mission_id}