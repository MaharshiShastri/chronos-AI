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
            timeout=1800,
            stream=True
        )
        buffer = ""
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    data = chunk.decode("utf-8")
                    for line in data.splitlines():
                        if not line.strip():
                            continue

                        buffer += chunk.decode("utf-8")

                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)

                            if not line.strip():
                                continue
                            
                        print(line)
                        json_data = json.loads(line)
                        yield json_data.get("response", "")

                except Exception as e:
                    print("JSON Error:", e)
                    continue
            
        if(response.status_code == 200):
            data = response.json()
            return data.get("response", "No response field in the API response.")
        
        else:
            return f"error: {response.status_code} - {response.text}"
        
    except requests.exceptions.RequestException as e:
        return "Error: Model took too long to respond."
    
    except Exception as e:
        return f"Error: {str(e)}"
    
