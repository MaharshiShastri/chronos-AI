import requests
import json
import subprocess
import time
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"
temperature = 0.2
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

ollama_running()

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
        if(response.status_code == 200):
            if not response.body():
                return {"error": "EMPTY_RESPONSE in generate_response in ai_service.py"}, 200
            data = response.json()
            return data.get("response", "No response field in the API response.")
        
        else:
            return f"error: {response.status_code} - {response.text}"
        
    except requests.exceptions.RequestException as e:
        return "Error: Model took too long to respond."
    
    except Exception as e:
        return f"Error: {str(e)}"

def generate_plan(task: str, total_time: int, mode: str):
    prompt = f"""[INST] <<SYS>>
You are a deterministic logic engine that outputs ONLY valid JSON arrays. 
Do not include any conversational text, notes, or markdown blocks.
<</SYS>>

Task: "{task}"
Total Time Budget: {total_time} seconds
Mode: {mode}

Constraint: Break this task into a logical sequence of 4 to 7 detailed steps.
The sum of "time_allocated" across all objects must equal exactly {total_time}.

REQUIRED JSON FORMAT:
[
  {{"step": "Detailed description of action", "time_allocated": 60}},
  {{"step": "Next logical action", "time_allocated": 120}}
]

Output the JSON array now:
[/INST]"""
    print('Inserted prompt: ', prompt)
    buffer = ""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "format": "json", # This is good, Ollama will try to force JSON
                "temperature": temperature,
                "stream": True
            },
            timeout=1800,
            stream=True
        )

        if response.status_code == 200:
            if not response.text:
                print("Ollama returned an empty response.")
                yield "data: {\"error\": \"Empty response from model in generate_plan.\"}\n\n"
                return
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    token = chunk.get("response", "")
                    print(repr(token))
                    yield token
        elif response.status_code == 500:
            print("Ollama server error detected. Restarting server...")
            subprocess.run(["taskkill", "/F", "/IM", "*ollama*"], capture_output=True)
            subprocess.Popen(["ollama",  "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            error_msg = f"Error: Ollama returned status {response.status_code}"
            print(error_msg, flush=True)
            yield error_msg
    
    except Exception as e:
        print(f"Planning error: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    

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
    
