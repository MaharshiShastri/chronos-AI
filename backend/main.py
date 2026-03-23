from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas import ChatRequest, ChatResponse
from ai_service import generate_response, generate_stream
from zoneinfo import ZoneInfo
import models
from database import Base, engine
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
@app.get("/")
def root():
    return {"message": "AI Backend Running"}

@app.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):

    #Temporary user 1
    user_id = 1

    if request.conversation_id:
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == request.conversation_id
            ).first()
    else:
        conversation = models.Conversation(user_id=user_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        #Save user message
    user_msg = models.Message(
        conversation_id = conversation.id,
        role="User",
        content = request.message
    )

    db.add(user_msg)
    messages = db.query(models.Message).filter(
    models.Message.conversation_id == conversation.id
).order_by(models.Message.timestamp.desc()).limit(6).all()
    history_text = ""

    for msg in messages:
        if msg.role == "user":
            history_txt += f"User: {msg.content}\n"
        else:
            history_txt = f"AI: {msg.content}\n"

    full_prompt = history_txt + f"User: {request.message}\nAssistant:"
    #GEnerate AI reply
    ai_reply = generate_response(full_prompt)

    #Save AI reply
    ai_msg = models.Message(
        conversation_id = conversation.id,
        role="LLM",
        content = ai_reply
    )

    db.add(ai_msg)
    db.commit()

    return {"repsonse": ai_reply, "conversation_id": conversation.id}

@app.get("/conversation/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):

    messages = db.query(models.Message).filter(models.Message.id == conversation_id).order_by(models.Message.timestamp).all()

    return [
        {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp
        }
        for msg in messages
    ]

@app.post("/chat-stream")
def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    user_id = 1

    if request.conversation_id:
        conversation = db.query(models.Conversation).filter(models.Conversation.id == request.conversation_id).first()

    else:
        conversation = models.Conversation(user_id = user_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    user_message = models.Message(conversation_id = conversation.id, role="user", content = request.message)

    db.add(user_message)
    db.commit()

    #Build context-aware prompt
    messages = db.query(models.Message).filter(models.Message.conversation_id == conversation.id).order_by(models.Message.timestamp.desc()).limit(6).all()
    messages = list(reversed(messages))

    history_txt = ""
    for msg in messages:
        role = "User" if msg.role == "user" else "AI"
        history_txt += f"{role}: {msg.content}\n"

    full_prompt = history_txt + f"{request.message}\nAI:"

    def stream():
        ai_response = ""
        try:
            for token in generate_stream(full_prompt):
                ai_response += token
                print(repr(token))
                yield token

            print("Done streaming")
        except Exception as e:
            print("ERROR IN STREAMING: ", str(e))
            yield b"\[ERROR]\n"
        finally:
            try:
                ai_msg = models.Message(
                    conversation_id = conversation.id,
                    role = "AI",
                    content = ai_response
                )

                db.add(ai_msg)
                db.commit()
                print("Saved AI progress")
            except Exception as e:
                print("DB ERROR:", str(e))

        
    return StreamingResponse(stream(), media_type="text/plain")