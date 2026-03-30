import requests
import json
import subprocess
import time
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

def ollama_running():
    try:
        requests.get(OLLAMA_URL, timeout=2)
    except requests.exceptions.ConnectionError:
        print("Ollama is not running. Starting server...")
        try:
            env = os.environ.copy()
            env['OLLAMA_DEBUG'] = "1"
            env["CUDA_VISIBLE_DEVICES"] = "1"
            subprocess.Popen(["ollama serve"], stdout = subprocess.DEVNULL, stderr= subprocess.DEVNULL, env=env)
            time.sleep(3)
        
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
            data = response.json()
            return data.get("response", "No response field in the API response.")
        
        else:
            return f"error: {response.status_code} - {response.text}"
        
    except requests.exceptions.RequestException as e:
        return "Error: Model took too long to respond."
    
    except Exception as e:
        return f"Error: {str(e)}"

def generate_plan(task: str, total_time: int, mode: str):
    prompt = f""""
    [INST] You are a logic-based planning engine.
Task: "{task}"
Budget: {total_time} seconds.
Mode: {mode}
Generate a JSON array of steps.
CRITICAL RULES:
1. Use ONLY the key "step" for the description.
2. Use ONLY the key "time_allocated" for the seconds.
3. Return ONLY the raw JSON array. No preamble, no "step1" keys, no "actions" keys.

FORMAT EXAMPLE:
[
  {{"step": "Shut off water", "time_allocated": 60}},
  {{"step": "Remove handle", "time_allocated": 120}}
]
[/INST]
    """
    print('Inserted prompt: ', prompt)
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":MODEL_NAME,
                "prompt" : prompt,
                "format": "json",
                "stream": True
            },
            timeout = 1800,
            stream=True
        )

        if response.status_code == 200:
            print(response)
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    token = chunk.get("response", "")
                    print(repr(token))
                    yield f"data: {json.dumps({'token': token})}\n\n"
                    
                    if chunk.get("done"):
                        return
        else:
            yield f"data: {json.dumps({'error': 'Ollama error status'})}\n\n"
        
        return [{"step": "Error: API Unreachable", "time_allocated" : total_time}] #Error
    
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
    
