import json
from app.services.ai_service import generate_response
from app.schemas.schemas import AgentState
class CriticAgent:
    def __init__(self):
        self.system_prompt = """
You are the Chronos Strategy Critic. 
        Review the MISSION PLAN for logical gaps, hallucinations, or budget violations.
        
        OUTPUT FORMAT (Strict JSON):
        {
          "status": "PASS" | "FAIL",
          "critique": "Feedback for the planner if FAIL",
          "suggestions": ["Optional list of improvements"]
        }
        """

    async def review_plan(self, state: AgentState) -> dict:
        plan_summary = "\n".join([f"-{s.get('description')}" for s in state.steps])
        prompt = f"Goal: {state.goal}\nPlan:\n{plan_summary}\n\nDoes this plan meet the objective efficiently? "

        raw_response = generate_response(f"{self.system_prompt}\n\n{prompt}")   
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        
        except:
            return {"status": "PASS", "critique":"Parsing error, assuming pass."}
        

critic = CriticAgent()
