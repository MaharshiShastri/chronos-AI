import time
import logging
from app.agents.orchestrator import orchestrator
from app.agents.critic import critic
from backend.app.services.browser_agent import browser_agent
from backend.app.services.code_executor import executor
from app.schemas.schemas import AgentState
from app.services.ai_service import generate_plan
from app.services.executor import run_mission_stream
from app.services import task_service

logger = logging.getLogger(__name__)

# backend/app/agents/workflow_service.py

class WorkflowService:
    async def finalize_mission(self, state: AgentState):
        """
        Missing method fix: Synthesizes the final output 
        from all tool execution steps.
        """
        summary = "Mission accomplished. "
        if state.tool_outputs:
            summary += f"Executed {len(state.tool_outputs)} steps successfully."
        
        return {
            "type": "chat", 
            "payload": summary,
            "meta": {"steps_completed": state.current_step_index}
        }
    
    async def route_and_resolve(self, user_input: str, db, user_id: int, time_budget: int = 600):
        start_time = time.time()
        state = AgentState(goal=user_input, status="active", tool_outputs={})
        
        iteration_count = 0
        while state.status != "completed" and iteration_count < 10:
            iteration_count += 1
            remaining = time_budget - (time.time() - start_time)

            # 1. ORCHESTRATION
            decision = await orchestrator.decide(state, int(remaining))
            print(f"Action is: ", decision["action"], "because: ", decision["reasoning"])
            # 2. PLANNING PHASE (If complex)
            if decision["action"] == "plan" and not state.steps:
                state.steps = await generate_plan(user_input, int(remaining))
                # CRITICISM: Verify the plan before starting
                review = await critic.review_plan(state.goal, state.steps)
                if review["status"] == "FAIL":
                    # Self-Correction: Re-plan with critic feedback
                    state.steps = await generate_plan(f"{user_input}. Fix: {review['critique']}")
            
            # 3. EXECUTION PHASE (The "Doing" Loop)
            if state.steps:
                for i in range(state.current_step_index, len(state.steps)):
                    step = state.steps[i]
                    
                    # Execute based on step type
                    output = await self.execute_single_step(step, state)
                    
                    # LOGGING & HISTORY (For Traceability)
                    state.tool_outputs[f"step_{i}"] = output
                    state.current_step_index += 1

                    # CRITIC: Check if step actually succeeded
                    step_review = await critic.review_step(step, output)
                    if step_review["status"] == "FAIL":
                        # Logic to retry or pivot
                        break 

            # 4. FINAL SYNTHESIS
            if state.current_step_index >= len(state.steps) or decision["action"] == "complete":
                state.status = "completed"
                return await self.finalize_mission(state)
    
    async def _initiate_mission_handoff(self, state, db, user_id):
        """
        Mirrors router_logic.py: Creates the DB records so the mission 
        can be tracked, rebalanced, and executed by executor.py
        """
        # 1. Create the Mission and Steps in DB (using your task_service)
        mission_id, enriched_steps = task_service.create_mission_and_steps(
            db, 
            user_id, 
            state.goal, 
            600, # Default budget
            state.steps
        )
        
        # 2. Update the state with the DB-assigned IDs
        state.mission_id = mission_id
        state.steps = enriched_steps # Now with STP-XXXX IDs from task_service
        
        return mission_id, enriched_steps
    
    async def execute_single_step(self, step, state):
        # Logic to route to browser_agent or executor based on step description
        if "search" in step['description'].lower():
            return await browser_agent.search_and_summarize(step['description'])
        return executor.execute_python(step.get('code', ''))
workflow = WorkflowService()