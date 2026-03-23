import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "tinyllama"

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
