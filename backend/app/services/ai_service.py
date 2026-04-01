import requests
import json
import subprocess
import time
import os
import logging

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"
temperature = 0.2
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def ollama_running():
    try:
        requests.get("http://localhost:11434/", timeout=2)
    except requests.exceptions.ConnectionError:
        print("Ollama is not running. Starting server...")
        try:
            print("Starting Ollama with GPU Discovery...")
            subprocess.Popen(["ollama",  "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
        
        except FileNotFoundError:
            print("Error: 'ollama' command not found. Please install ollama")

ollama_running() #To initialize ollama server on its own

def generate_response(prompt) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )
        
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "data": result.get("response", ""),
                "error": None
            }
        
        return {"success": False, "data": None, "error": f"API_STATUS_{response.status_code}"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {"success": False, "data": None, "error": "REQUEST_TIMEOUT"}

def generate_plan(task: str, total_time: int, mode: str):
    prompt = f"""[INST] <<SYS>>
You are a project management assistant. 
Output ONLY a JSON array containing EXACTLY 5 to 7 objects.
Each object must have "step" and "time_allocated".
The sum of all "time_allocated" values MUST be exactly {total_time}.
<</SYS>>

Task: "{task}"
Total Time: {total_time} seconds

Example of 5 steps adding to {total_time}:
[
  {{"step": "Step 1...", "time_allocated": {total_time // 5}}},
  {{"step": "Step 2...", "time_allocated": {total_time // 5}}},
  ...
]

JSON Array:
[/INST]"""
    buffer = ""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "format": "json", 
                "temperature": temperature,
                "num_predict": 1000, 
                "stream": True
            },
            timeout=180,
            stream=True
        )

        if response.status_code == 200:
            if not response.text:
                print("Ollama returned an empty response.")
                yield json.dumps({"error": f"Service Error {response.status_code}"})
                return
            
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    token = chunk.get("response", "")
                    yield token

        elif response.status_code == 500:
            print("Ollama server error detected. Restarting server...")
            subprocess.run(["taskkill", "/F", "/IM", "ollama*"], capture_output=True)
            subprocess.Popen(["ollama",  "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            error_msg = f"Error: Ollama returned status {response.status_code}"
            print(error_msg, flush=True)
            yield error_msg
    
    except Exception as e:
        print(f"Planning error: {e}")
        logger.error(f"Streaming error: {e}")
        yield json.dumps({"error": "STREAM_FAILURE"})
    

def generate_stream(prompt: str):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": True
            },
            timeout=180,
            stream=True
        )
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode("utf-8"))
                token = data.get("response", "")
                #print(repr(token))
                yield token

                if data.get("done"):
                    return
                
                    
    except Exception as e:
        print("STREAM ERROR:", str(e))
        yield "[ERROR]"
    
