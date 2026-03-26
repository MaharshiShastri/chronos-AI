import requests
import json
import subprocess
import time
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

def ollama_running():
    try:
        requests.get("https://localhost:11434/", timeout=2)
    except requests.exceptions.ConnectionError:
        print("Ollama is not running. Starting server...")
        try:
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = "1"
            subprocess.Popen(["ollama", "serve"], stdout = subprocess.DEVNULL, stderr= subprocess.DEVNULL, env=env)
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

def generate_plan(task: str, total_time: int, mode: str) -> list:
    prompt = f""""
    You are a time-constrained planning agent.
    Task: "{task}"
    Total Time Budget: {total_time} seconds.
    Mode: {mode} (fast = brief steps, deep = detailed steps).

    Break this task into exactly 3-5 logical steps.
    Allocate a portion of total {total_time} seconds to each step.
    Return ONLY a JSON array of objects with "step" and "time_allocated" keys.
    Example: [{{"step": "Analyze", "time_allocated": 30}} ]
    """

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model":MODEL_NAME,
                "prompt" : prompt,
                "format": "json",
                "stream": False
            },
            timeout = 180
        )

        if response.status_code == 200:
            raw_content = response.json().get("response", "")
            data = json.loads(raw_content)
            if isinstance(data, dict):
                for key in ["plan", 'steps', 'tasks']:
                    if key in data: return data[key] #Return the dictionary values of plan
                return [data] #Return dictionary as the string 
            return data #Return the raw data recieved
        
        return [{"step": "Error: API Unreachable", "time_allocated" : total_time}] #Error
    
    except Exception as e:
        print(f"Planning error: {e}")
        return[{"step": "Execute Task", "time_allocated":total_time}]
    

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
                yield token

                if data.get("done"):
                    return
                
                    
    except Exception as e:
        print("STREAM ERROR:", str(e))
        yield "[ERROR]"
    
