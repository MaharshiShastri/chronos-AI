import requests
import json
import subprocess
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "tinyllama"

def ollama_running():
    try:
        requests.get("https://localhost:11434/", timeout=2)
    except requests.exceptions.ConnectionError:
        print("Ollama is not running. Starting server...")
        try:
            subprocess.Popen(["ollama", "serve"], stdout = subprocess.DEVNULL, stderr= subprocess.DEVNULL)
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
    
