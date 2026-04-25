#The master of the Agentic AI - the one who handles workflow of the agents

import json
from typing import Dict, Any
from backend.app.services.ai_service import generate_response
from backend.app.schemas.schemas import AgentState
import logging

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self):
        self.system_prompt = """
        You are the Chronos-AI Central Orchestrator. 
        Your goal is to decide the NEXT ACTION in a multi-agent system.
        
        AVAILABLE ACTIONS:
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
    
    async def decide(self, state: AgentState ) -> Dict:
        context = f"Goal: {state.goal}\nSteps taken: {state.current_step_index}\nTool Outputs: {state.tool_outputs}"
        prompt = f"{context}\n\nDecision (JSON):"

        raw_response = generate_response(prompt)
        try:
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            return {"action": "chat", "reasoning": "Fallback"}
        
orchestrator = Orchestrator()