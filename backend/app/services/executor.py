import asyncio
import time
import logging
import json
from app.services.optimizer import TimeOptimizer
from app.services.ai_service import generate_stream

logger = logging.getLogger(__name__)

def perform_task():
    pass

ACTIVE_MISSIONS = {}

async def safe_json_parse(text: str, default: dict) -> dict:
    try:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)

    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"LLM payload malformed: {e} | Raw: {text}")
        return default
    

async def evaluate_step_actionability(step_description: str) -> dict:
    prompt = f"""
    Evaluate if the following task step is actionable or ambiguous.
    Step: "{step_description}"
    
    If it's actionable (clear what to do), respond with: {{"status": "CLEAR"}}
    If it's ambiguous (needs paths, keys, or details), respond with: {{"status": "AMBIGUOUS", "reason": "brief explanation"}}
    
    Respond ONLY in JSON: {{\"status\": \"CLEAR\"}} or {{\"status\": \"AMBIGUOUS\", \"reason\": \"...\"}}.
    """
    
    try:
        response_text = await generate_stream(prompt)
        return await safe_json_parse(response_text, {"status": "CLEAR"})
    except asyncio.TimeoutError:
        return {"status": "CLEAR"}


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

async def run_mission_stream(mission_id: int, total_budget: int, manifest: list):
    metrics = {
        "steps_completed" : 0,
        "total_tokens" : 0,
        "interrupts" : 0
    }
    # Store the manifest in the global state so the PATCH route can find it
    ACTIVE_MISSIONS[mission_id] = manifest
    start_time = time.time()
    
    try:
        for i, step in enumerate(manifest):
            elapsed_time = time.time() - start_time
            manifest = TimeOptimizer.rebalance_manifest(manifest, i-1, float(total_budget), float(elapsed_time))
            strategy = TimeOptimizer.get_execution_strategy(float(total_budget), float(elapsed_time))

            if elapsed_time >= total_budget:
                yield{"event":"MISSION_TERMINATED", "reason" : 'HARD_BUDGET_EXCEEDED'}
                return
            
            step_start_marker = time.time()
            if strategy == "NORMAL":
                evaluation = await evaluate_step_actionability(step['description'])
                if evaluation.get('status').lower() == "ambiguous":
                    metrics["interrupts"] += 1
                    step['status'] = 'awaiting_clarification'
                    yield {
                        "event" : "STRATEGIC_INTERRUPT",
                        "step_id" : step["backend_step_id"],
                        "reason" : evaluation.get("reason", "Incomplete instructions detected.")
                    }

                    wait_time = time.time()
                    while step['status'] == "awaiting_clarification":
                        await asyncio.sleep(1)
                        if(time.time() - wait_time) > 300:
                            step['status'] = "timed_out"
                            yield {"event" : "TIMEOUT_ABORT", "reason":"No user response for 5 minutes"}
                            return 

            
            # 1. Update In-Memory Status
            step['status'] = "started"
            
            yield {
                "event": "STEP_STARTED",
                "index": i,
                "step_id": step['backend_step_id'], # Fixed: matches router + removed extra comma typo
                "time_remaining": round(max(0, total_budget - (time.time() - start_time)), 2)
            }

            # 2. Simulation Logic
            allocated_time = step['time_allocated']
            artifact = f"Generated content for: {step['description']}"
            
            # 3. Update In-Memory Details
            step['artifact_content'] = artifact
            step['status'] = "awaiting_approval"

            await asyncio.sleep(min(allocated_time, 2))

            actual_duration = time.time() - step_start_marker
            metrics["steps_completed"] += 1
            yield {
                "event" : "TELEMETRY_PULSE",
                "metrics" : {
                    "step_latency": round(actual_duration * 1000, 2),
                    "interrupt_count": metrics["interrupts"],
                    "progress": f"{metrics['steps_completed']}/{len(manifest)}"
                }
            }
            step['actual_duration'] = actual_duration
            drift = actual_duration - allocated_time
            
            yield {
                "event": "REQUIRE_APPROVAL",
                "index": i,
                "step_id": step['backend_step_id'],
                "content": {
                    "artifact": artifact, 
                    "time_needed": round(actual_duration, 2), 
                    "drift": round(drift, 2) if drift > 0 else 0
                },
                "instructions": "Please approve or provide feedback."
            }
            
            # 4. THE IN-MEMORY APPROVAL LOOP (No DB polling)
            approval_window = 60 if strategy == "NORMAL" else 10
            if strategy == 'EMERGENCY':
                step['status'] = 'completed'
                logger.info(f'Auto-approving step {i} due to human inactivity.')
            else:
                approval_start = time.time()
                while step['status'] == "awaiting_approval":
                    await asyncio.sleep(1) 
                    if(time.time() - approval_start) > approval_window:
                        step['status'] = 'completed'
                        logger.info(f'Auto-approving step {i} due to human inactivity.')
                
            yield {
                "event": "STEP_COMPLETED",
                "index": i,
                "actual_duration": round(actual_duration, 0)
            }

        # 5. Finalize Mission - This is where the DB is finally touched
        yield {
            "event": "MISSION_COMPLETED", 
            "mission_id": mission_id, 
            "time_completion": round(time.time() - start_time, 0),
            "metrics": {
                "execution_time": f"{round(time.time() - start_time, 2)}s",
                "interrupt_count": metrics["interrupts"],
            }
        }

    finally:
        # Cleanup global memory when stream closes or finishes
        if mission_id in ACTIVE_MISSIONS:
            del ACTIVE_MISSIONS[mission_id]
