#The master of the Agentic AI - the one who handles workflow of the agents

import json
from typing import Dict, Any
from app.services.ai_service import generate_response
from app.schemas.schemas import AgentState
import logging

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.system_prompt = """
        You are the Chronos-AI Central Orchestrator. 
        Your goal is to decide the NEXT ACTION in a multi-agent system.
        Decide the NEXT ACTION based on the Goal and REMAINING TIME.
        
        CRITICAL TIME RULES:
        - If Time < 10% of budget: Force "complete" or "chat".
        - If Goal is complex and Time > 50%: Use "plan".
        
        AVAILABLE ACTIONS:
        - "chat": User wants to converse.
        - "plan": User has a complex goal requiring a strategy.
        - "retrieve": User is asking about specific facts, past files, or Vault data.
        - "execute": User has approved a plan or is giving a direct command to act.
        - "ask_user": Input is vague, contradictory, or missing parameters.
        - "web_search": Task requires external data (Web).
        - "code_execution" : If the user asks for complex math, data analysis, or logic that requires calculation.

        OUTPUT FORMAT (Strict JSON):
        {
          "action": "plan|retrieve|execute|ask_user|web_search|code_execution",
          "reasoning": "Why this action?",
          "confidence": 0.0-1.0
        }
        """
    
    async def decide(self, state: AgentState, remaining_time: int ) -> Dict:
        history_summary = "\n".join([f"- {k}: {str(v)[:200]}..." for k, v in state.tool_outputs.items()])
        context = (
            f"MISSION_GOAL: {state.goal}\n"
        f"TIME_REMAINING: {remaining_time}s\n"
        f"TOOL_HISTORY_SO_FAR:\n{history_summary if history_summary else 'No tools used yet.'}\n"
        f"CURRENT_ITERATION: {len(state.tool_outputs)}"
        )
        prompt = f"{self.system_prompt}\n\n{context}\n\nDecision (JSON):"

        raw_response = generate_response(prompt)
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            return {"action": "chat", "reasoning": "Fallback"}
        
orchestrator = Orchestrator()