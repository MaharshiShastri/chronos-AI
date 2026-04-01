from fastapi import APIRouter, Depends, HTTPException, status, FastAPI
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from jose import jwt, JWTError
import json
import uuid
import re

# Internal Imports (User-defined modules and methods)
from database import SessionLocal
from app.schemas.schemas import ChatRequest, ChatResponse, UserAuth, PlanResponse, PlanRequest, StatusUpdate
from app.services.ai_service import generate_response, generate_stream, generate_plan
import app.models.models as models
from app.core.auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.services.executor import run_mission_stream, pending_approvals
from fastapi.security import OAuth2PasswordBearer
from app.services import chat_service, task_service

api_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@api_router.get("/")
def root():
    return {"message": "AI Backend Running"}

#Retrieve Current user details from token
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    #Recieve the token and check if the ser exists, if user exists, return user details, else return credentials_exception error
    
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

#Signup page
@api_router.post("/signup")
def signup(request: UserAuth, db: Session = Depends(get_db)):
    #Check if email already exists, if so, reject, if not then create new user with hashed password and save to database

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

#Login Page
@api_router.post("/login")
def login(request: UserAuth, db: Session = Depends(get_db)):
    #Check if user exists, if not raise HTTPexception, if they do, then match their password and email and provide token if
    # valid credentials and return the token to user's localItem 
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code = 401, detail = "Invalid Credentials!")
    
    access_token = create_access_token(data={"sub": user.email})
    return ({"access_token": access_token, "token_type": "bearer", "user": {"id": user.id,  "email": user.email}})

#START of Ordinary conversations with AI functions below for web-equivalent CRUD operations
#Update the conversation with new prompt from user(buffererd response used for very initial testing)
@api_router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Check if the conversation is presnet, if not then create a new one
    if request.conversation_id:
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == request.conversation_id
            ).first()
    else:
        conversation = models.Conversation(user_id=current_user.id)
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

    return {"response": ai_reply, "conversation_id": conversation.id}

#Read opearation of web-equivalent(GET) for all conversations
@api_router.get("/conversation/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Retrieve a list of conversations of the user, based on matching the conversation's user id and user's id, 
    # retrieve the previous messages by matching conversation id of database and request.
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
#Update the conversation with new prompt from user(streaming response used for live deployment)
@api_router.post("/chat-stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Check if conversation exists, or create a new one and post the prompt in new conversation and return a streaming repsonse
    #to simulate the AI human-like thinking and saving time and bandwith
    # 1. Handle Conversation Lookup/Creation
    conversation = chat_service.get_or_create_conversation(db, current_user.id, request.conversation_id, request.message)

    # 2. Save User Message immediately
    chat_service.save_message(db, conversation, "user", request.message)
    full_prompt = chat_service.build_chat_history(db, conversation.id, request.message)

    async def stream_generator():
        ai_response = ""
        try:
            # generate_stream should be your generator calling Ollama
            for token in generate_stream(full_prompt):
                ai_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Send the ID at the end so the frontend can save it for the next turn
            yield f"data: {json.dumps({'conversation_id': conversation.id})}\n\n"

        except Exception as e:
            print(f"STREAM ERROR: {e}")
            yield f"data: {json.dumps({'error': 'Connection Interrupted'})}\n\n"

        finally:
            # 4. Save AI Response to DB
            chat_service.save_message(db, conversation.id, "AI", ai_response)

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

#Read of web-quivalent method
@api_router.get('/conversations')
def get_user_conversations(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Retrieve a list of conversations for the sidebar to give users the chance to go back to jumpt between conversations
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

#Delete of web-equivalent method    
@api_router.delete("/conversation/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Check if the conversation_id is present in DB, if not then raise an error,
    #If present, then delete the conversation along with messages of the converation(via enabling CASCADE)
    conv = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id,
        models.Conversation.id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    
    db.delete(conv)
    db.commit()
    return{"message": "Conversation deleted successfully!"}

#Update of web-equivalent method
@api_router.patch("/conversation/{conversation_id}")
def update_title(conversation_id: int, title: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Check if the retreieved id present, if present then rename, if not then raise HTTPException
    conv = db.query(models.Conversation).filter(
        models.Conversation.user_id == current_user.id,
        models.Conversation.id == conversation_id
    ).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied")
    
    conv.title = title
    db.commit()
    return {"title": conv.title, "id": id}
#END of Ordinary conversations with AI functions below for web-equivalent CRUD operations
#START of Agentic AI with time-awareness engine conversations with functions below for web-equivalent CRUD operations
#Create function of web-equivalent method
@api_router.post("/plan")
async def create_execution_plan(request: PlanRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    async def plan_generator():
        accumulated_json = ""
        try:
            # 1. STREAM FROM AI
            # Note: Ensure generate_plan is actually yielding strings
            for token in generate_plan(request.task, request.time_budget, request.mode):
                accumulated_json += token

            raw_steps = task_service.clean_and_parse_plan(accumulated_json)
            if not raw_steps:
                yield f"data: {json.dumps({'error': "Failed to parse a plan"})}"

            mission_id, enriched = task_service.create_mission_and_steps(db, current_user.id, request.task, request.time_budget, raw_steps)

            yield f"data: {json.dumps({'mission_id': mission_id, 'enriched_steps': enriched, 'status': 'complete'})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(plan_generator(), media_type="text/event-stream")

#Read function of web-equivalent method
@api_router.get("/tasks")
def get_tasks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Return a list of previously given task to access them
    return db.query(models.Tasks).filter(models.Tasks.user_id == current_user.id).order_by(models.Tasks.created_at.desc()).all()
#Delete function of web-equivalent
@api_router.delete("/task/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Delete a task based on task_id recieved from user, if such task does not exist, then return a raise HTTPException
    task = db.query(models.Tasks).filter(
        models.Tasks.user_id == current_user.id,
        models.Tasks.id == task_id
    ).first()
    if not task:
        raise HTTPException(status_code = 404, detail="Task not found or access denied")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully!"}

#Update function of web-equivalent
@api_router.patch("/task/{task_id}")
def update_task_status(task_id: int, data: StatusUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    #Update the task status, whether it is "pending" or "completed", if such a task exists, if no such task exists then 
    #return a HTTPException
    task = db.query(models.Tasks).filter(
        models.Tasks.user_id == current_user.id,
        models.Tasks.id == task_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = data.status 
    
    db.commit()
    return {"status": task.status}

#Read funtion of web-equivalent
@api_router.get("/execute/{mission_id}")
async def start_execution(mission_id: int, db:Session = Depends(get_db)):
    #Once the step is approved, execute it here, remove from current list of steps
    #Do this until the entire task list is completed
    task = db.query(models.Tasks).filter(models.Tasks.id == mission_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Mission not found")

    steps_query = db.query(models.TaskStep).filter(models.TaskStep.task_id == mission_id).all()
    steps = [
        {"step_id": s.backend_step_id, "step": s.description, "time_allocated": s.time_allocated}
        for s in steps_query
    ]

    async def event_generator():
        print(f"Starting execution for mission {mission_id} with steps: {steps}")
        try:
            async for event in run_mission_stream(mission_id, steps, task.total_time):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'ERROR', 'detail': str(e)})}\n\n"

        finally:
            if mission_id in pending_approvals:
                del pending_approvals[mission_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@api_router.patch("/execute/{mission_id}/approve")
async def start_execution(mission_id: int, data: dict, step_id: str, db: Session = Depends(get_db)):
    #An asynchronous function meant to stream set of tasks, check if such a task(mission) exists, if not then raise HTTPException,
    #If task(mission) does exist, then plan the task and give plan to the user before actaully executing the steps in task list and wait for approval
    #The user can whether let the system continue(approve) or update the content(as done below) and then approve
    #Once approved and step is completed, then go to GET /execute/{mission_id} for further work

    step = db.query(models.TaskStep).filter(models.TaskStep.task_id == mission_id, models.TaskStep.backend_step_id == step_id).forst()

    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    if (data.get("content")):
        step.artifact_content = data.get("content")
        step.status = "refined"

    db.commit()
    return {"message": "Step approved in DB. Executor resuming..."}
