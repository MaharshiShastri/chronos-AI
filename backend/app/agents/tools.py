import subprocess
import os
import logging

logger = logging.getLogger(__name__)

class ToolAgent:
    async def execute_python(self, code: str) -> str:
        #Execute python here in a restricted subprocess

        forbidden = ['os.remove', 'shutil', 'subprocess', 'eval(', 'exec(', 'open(']
        if any(f in code for f in forbidden):
            return "ERROR: Security Violation - forbidden command found."
        
        try:
            process = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=5
            )

            if process.returncode == 0:
                return f"OUTPUT:\n{process.stdout}"
            
            return f"ERROR:\n{process.stderr}"
        
        except subprocess.TimeoutExpired:
            return "ERROR: Process timed out (Max 5s)."
        
        except Exception as e:
            return f"SYSTEM_ERROR: {str(e)}" 
        
    async def web_search(self, query: str) -> str:
        return f"SEARCH_RESULT: Real Time data for '{query}' would be fetched here."
    
tool_agent = ToolAgent()

