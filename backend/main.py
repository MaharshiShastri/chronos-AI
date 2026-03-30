from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sympy import re
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
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "login")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5500", "http://localhost:5173"],
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

    # 1. Handle Conversation Lookup/Creation
    if request.conversation_id:
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == request.conversation_id,
            models.Conversation.user_id == user_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=403, detail="SESSION NOT FOUND")
    else:
        conversation = models.Conversation(user_id=user_id, title=request.message[:30])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 2. Save User Message immediately
    user_message = models.Message(conversation_id=conversation.id, role="user", content=request.message)
    db.add(user_message)
    db.commit()

    # 3. Build Context (Fetch last 6 messages INCLUDING the one we just saved)
    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation.id
    ).order_by(models.Message.timestamp.desc()).limit(6).all()
    
    # Reverse so they are in chronological order
    context_history = list(reversed(messages))

    history_txt = ""
    for msg in context_history:
        role = "User" if msg.role == "user" else "AI"
        history_txt += f"{role}: {msg.content}\n"

    # The prompt now includes the history (which already has the current message)
    full_prompt = f"{history_txt}AI:"

    async def stream_generator():
        ai_response = ""
        try:
            # generate_stream should be your generator calling Ollama
            for token in generate_stream(full_prompt):
                ai_response += token
                print(repr(token))
                yield f"data: {json.dumps({'token': token})}\n\n"
            
            print(conversation.id)
            # Send the ID at the end so the frontend can save it for the next turn
            yield f"data: {json.dumps({'conversation_id': conversation.id})}\n\n"

        except Exception as e:
            print(f"STREAM ERROR: {e}")
            yield f"data: {json.dumps({'error': 'Connection Interrupted'})}\n\n"
        finally:
            # 4. Save AI Response to DB
            if ai_response:
                try:
                    # We create a new message object
                    new_ai_msg = models.Message(
                        conversation_id=conversation.id,
                        role="AI",
                        content=ai_response
                    )
                    db.add(new_ai_msg)
                    db.commit()
                    print(f"Saved AI response to conversation {conversation.id}")
                except Exception as e:
                    db.rollback()
                    print(f"DB SAVE ERROR: {e}")

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.post("/plan")
async def create_execution_plan(request: PlanRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user_id = current_user.id

    new_mission = models.Tasks(
        user_id=user_id,
        title=request.task[:50],  # Use first 50 chars of request as title
        total_time=request.time_budget,
        status="pending"
    )

    db.add(new_mission)
    db.commit()
    db.refresh(new_mission)

    async def plan_generator():
        accumulated_json = ""
        try:
            # 1. STREAM FROM AI
            # Note: Ensure generate_plan is actually yielding strings
            for token in generate_plan(request.task, request.time_budget, request.mode):
                accumulated_json += token
            
            import re
            match = re.search(r'\[.*\]', accumulated_json, re.DOTALL)
            if match:
                clean_json = match.group(0)
                clean_json = clean_json.replace("}{", "},{")
                raw_steps = json.loads(clean_json)
            else:
                found_objects = re.findall(r'\{[^{}]*\}', accumulated_json, re.DOTALL)
                raw_steps = [json.loads(obj) for obj in found_objects]

            if raw_steps:
                enriched_steps = []
                for idx,s in enumerate(raw_steps):
                    desc = s.get("step") or s.get("description") or "No description"
                    step_entry = models.TaskStep(
                        task_id=new_mission.id,
                        backend_step_id=f"STP-{uuid.uuid4().hex[:6].upper()}",
                        description=desc,
                        time_allocated=s.get("time_allocated", 60),
                        order=idx
                    )
                    db.add(step_entry)
                    enriched_steps.append({
                        "step_id": step_entry.backend_step_id,
                    "step": step_entry.description,
                    "time_allocated": step_entry.time_allocated
                    })
                    print(enriched_steps)
                db.commit()
                yield f"data: {json.dumps({'mission_id': new_mission.id, 'enriched_steps': enriched_steps, 'status': 'complete'})}\n\n"
            else:
                yield f"data: {json.dumps({'error': "No valid plan steps found"})}\n\n"

        except Exception as e:
            db.rollback()
            print(f"Generator Error: {e}")
            print(f"JSON Partial Parse Error: {e}")
            # Fallback: Try to find any valid JSON objects inside the mess
            import re
            found_objects = re.findall(r'\{.*?\}', accumulated_json, re.DOTALL)
            raw_steps = [json.loads(obj) for obj in found_objects]
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(plan_generator(), media_type="text/event-stream")
    
@app.get('/conversations')
def get_user_conversations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    conversations = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id
    ).order_by(models.Conversation.id.desc()).all()

    return [
        {
            "id": conversation.id,
            "title": conversation.title if conversation.title else f"Conversation {conversation.id}",
            "created_at": conversation.timestamp.isoformat() if hasattr(conversation, 'timestamp') else None
        }
        for conversation in conversations
    ]

@app.delete("/conversation/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    conv = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id,
        models.Conversation.id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    
    db.delete(conv)
    db.commit()
    return{"message": "Conversation deleted successfully!"}

@app.patch("/conversation/{conversation_id}")
@app.patch("/conversation/{conversation_id}")
def update_title(conversation_id: int, title: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Use conversation_id, not id
    conv = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id,
        models.Conversation.id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    
    conv.title = title
    db.commit()
    return {"title": conv.title}

@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Tasks).filter(models.Tasks.user_id == current_user.id).order_by(models.Tasks.created_at.desc()).all()
