import time
import logging
from app.agents.orchestrator import orchestrator
from app.agents.critic import critic
from app.agents.browser_agent import browser_agent
from app.agents.code_executor import executor
from app.schemas.schemas import AgentState


logger = logging.getLogger(__name__)

class WorkflowService:
    async def route_and_resolve(self, user_input: str, db, user_id: int, time_budget: int = 600):
        # 1. Initialize the Unified State (Inter-Agent Comm starts here)
        state = AgentState(
            goal=user_input,
            status="init",
            tool_outputs={}
        )
        
        start_time = time.time()
        
        # 2. Orchestrator Decides the path
        decision = await orchestrator.decide(state)
        state.status = "routing"
        
        # 3. Time-Aware Branching
        if decision["action"] == "plan":
            from app.services.ai_service import generate_plan
            # Ensure time budget is passed to the planner
            state.steps = await generate_plan(state.goal, time_budget, "Fast", "")
            
            # Critic Review
            review = await critic.review_plan(state)
            if review["status"] == "FAIL":
                state.critic_feedback = review["critique"]
                # Re-plan with feedback
                state.steps = await generate_plan(state.goal, time_budget, "fast", state.critic_feedback)

            return {"type": "plan", "payload": state.steps, "meta": decision}

        if decision["action"] == "web_search":
            results = await browser_agent.search_and_summarize(state.goal)
            state.tool_outputs["web_search"] = results
            
            # Grounding logic
            context = "\n".join([f"Source: {r['title']}" for r in results])
            return {"type": "chat", "payload": context, "meta": decision}

        if decision["action"] == "code_execution":
            from app.services.ai_service import generate_response
            script = generate_response(f"Write python for: {state.goal}")
            output = executor.execute_python(script)
            state.tool_outputs["code_output"] = output
            
            return {"type": "chat", "payload": f"Result: {output}", "meta": decision}

        return {"type": "chat", "meta": decision}

workflow = WorkflowService()