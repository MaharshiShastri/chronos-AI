import sys
import io
import contextlib
import logging

logger = logging.getLogging(__name__)

class CodeExecutor:
    def __init(self, code:str):
        f = io.StringIO()
        logger.info("🛠️ CodeExecutor: Running dynamic script...")

        with contextlib.redirect_stdout(f):
            try:
                forbidden = ["os", "shutil", "subprocess", "socket"]
                if any(f"import {mod}" in code or f"from {mod}" in code for mod in forbidden):
                    return "Error: Use of restricted libraries detected."
                
                exec(code, {'__builtins__': __builtins__}, {})
            except Exception as e:
                return f"Execution Error: {str(e)}"
        
        return f.getvalue()
    
executor = CodeExecutor()