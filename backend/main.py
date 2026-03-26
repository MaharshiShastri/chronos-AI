from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal
from schemas import ChatRequest, ChatResponse, UserAuth, PlanResponse, PlanRequest
from ai_service import generate_response, generate_stream, generate_plan
from zoneinfo import ZoneInfo
import models
from database import Base, engine
from fastapi.responses import StreamingResponse
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from datetime import datetime

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:8000", "http://localhost:5500"],
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
# WARNING: This deletes everything every time the server restarts!
# Useful only during heavy development/debugging, do not unnecessarily un-comment the next line.
#Base.metadata.drop_all(bind=engine) !!<- DO NOT UNCOMMENT UNLESS FORCED TO
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "AI Backend Running"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()

    if user is None:
        raise credentials_exception
    
    return user


@app.post("/signup")
def signup(request: UserAuth, db: Session = Depends(get_db)):

    existing_user = db.query(models.User).filter(models.User.email == request.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail= "Email already registered")
    hashed_password = hash_password(request.password)
    new_user = models.User(
        email = request.email,
        password_hash = hashed_password
    )

    db.add(new_user)
    db.commit()
    return {"message" : "User created successfully!"}

@app.post("/login")
def login(request: UserAuth, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code = 401, detail = "Invalid Credentials!")
    
    access_token = create_access_token(data={"sub": user.email})
    return ({"access_token": access_token, "token_type": "bearer", "user": {"id": user.id,  "email": user.email}})

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
            history_text += f"User: {msg.content}\n"
        else:
            history_text += f"AI: {msg.content}\n"

    full_prompt = history_text + f"User: {request.message}\nAssistant:"
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
def get_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    conversation = db.query(models.Message).filter(
        models.Conversation.id == conversation_id,
        models.Conversation.user_id == current_user.id
        ).first()
    if not conversation:
        raise HTTPException(status_code=403, detail="ACCESS DENIED: Unauthorized Access")
    
    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id,
        models.Conversation.user_id == current_user.id
        ).order_by(models.Message.timestamp.asc()).all()

    return [
        {
            "role": msg.role.lower(),
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
        }
        for msg in messages
    ]

@app.post("/chat-stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user_id = current_user.id

    if request.conversation_id:
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == request.conversation_id,
            models.Conversation.user_id == current_user.id
        ).first()

        if not conversation:
            raise HTTPException(status_code=403, detail="SESSION NOT FOUND")
    else:
        conversation = models.Conversation(user_id = user_id, title=request.message[:20])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    user_message = models.Message(conversation_id = conversation.id, role="user", content = request.message)

    current_time = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    db.add(user_message)
    db.commit()

    #Build context-aware prompt
    messages = db.query(models.Message).filter(models.Message.conversation_id == conversation.id).order_by(models.Message.timestamp.desc()).limit(6).all()
    messages = list(reversed(messages))

    history_txt = ""

    for msg in messages:
        role = "User" if msg.role == "user" else "AI"
        history_txt += f"{role}: {msg.content}\n"

    full_prompt = f"{history_txt}\nUser: {request.message}\nAI:"

    def stream():
        ai_response = ""
        try:
            for token in generate_stream(full_prompt):
                ai_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            
            yield f"data: {json.dumps({'conversation_id': conversation.id})}\n\n"

        except Exception as e:
            print("ERROR IN STREAMING: ", str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
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

        
    return StreamingResponse(stream(), media_type="text/event-stream")

@app.post("/plan", response_model= PlanResponse)
async def create_execution_plan(request: PlanRequest, current_user: models.User = Depends(get_current_user)) :
    #Analyze a task and returns a timed breakdwon
    try:
        plan_data = generate_plan(request.task, request.time_budget, request.mode)
        return {
            "plan": plan_data,
            "total_time": request.time_budget
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))