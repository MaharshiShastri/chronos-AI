from fastapi import FastAPI
from schemas import ChatRequest, ChatResponse
from ai_service import generate_response

app = FastAPI()

@app.get("/")
def root():
    return {"message": "AI Backend Running"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    user_message = request.message

    ai_reply = generate_response(user_message)
    return ChatResponse(response=ai_reply)