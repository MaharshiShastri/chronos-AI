import sys
import io
import contextlib
import logging

logger = logging.getLogger(__name__)

class CodeExecutor:
    def execute_python(self, code: str):
        # 1. Restricted Global Environment
        safe_locals = {}
        safe_globals = {
            "__builtins__": {
                "print": print, "range": range, "len": len, "int": int, "float": float,
                "list": list, "dict": dict, "sum": sum, "max": max, "min": min
            }
        }
        
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, safe_globals, safe_locals)
            return stdout.getvalue()
        except Exception as e:
            logger.warning(f"Execution runtime intercept: {str(e)}")
            return f"Runtime Error: {str(e)}"
        
executor = CodeExecutor()