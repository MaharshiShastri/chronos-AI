import os
import json
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
import asyncio
import fitz

#Internal import
from database import SessionLocal
from app.core.auth import hash_password, verify_password, create_access_token
from app.core.security import get_current_user, oauth2_scheme
from app.schemas.schemas import ChatRequest, UserAuth, StepApprovalRequest, PlanRequest, StatusUpdate, MemoryCreate
from app.models import models

#Service and workers
from app.services import chat_service
from app.services.memory_service import get_memories, add_memory, delete_memory, update_memory
from app.services.task_service import trigger_mission_execution
from app.services.document_service import save_and_ingest_document
from app.services.celery_app import celery, r_client
from app.services.tasks import process_chat_task, process_plan_task
from app.utils.analytics import analytics_engine

logger = logging.getLogger(__name__)

api_router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def validate_input(text: str):
    if not text:
        return
    
    forbidden_keywords = ["IGNORE ALL PREVIOUS INSTRUCTIONS", "SYSTEM_OVERRIDE"]
    if any(key in text.upper() for key in forbidden_keywords):
        raise HTTPException(status_code=403, detail="Instruction Injection Detected.")
    
def classify_failure(error_type: str, detail: str = ""):
    mapping = {
        "UNAUTHORIZED_ACCESS": {"code": "ERR_AUTH_403", "severity": "CRITITCAL"},
        "DB_CONTENT": {'code': "ERR_DB_500", "severity": "HIGH"}
    }

    meta = mapping.get(error_type, {"code": "ERR_UNKNOWN", 'severity': "UNKNOWN"})
    return {"error": meta, "detail": detail, "timestamp": time.time()}

#Root and Identity routers

@api_router.get("/")
def root():
    return {"message": "Chronos AI Backend Running."}

@api_router.post("/signup")
def signup(request: UserAuth, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    
    new_user = models.User(email=request.email, password_hash=hash_password(request.password))
    db.add(new_user)
    db.commit()
    return {"message": "User Created successfully"}

@api_router.post("/login")
def login(request: UserAuth, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": user.id, "email": user.email}}

#Conversation Management
@api_router.get('/conversations')
def get_user_conversations(db: Session=Depends(get_db), current_user: models.User = Depends(get_current_user)):
    conversations = db.query(models.Conversation).filter(models.Conversation.user_id == current_user.id).order_by(models.Conversation.id.desc()).all()

    return [
        {
            "id": c.id,
            "title": c.title if c.title else f"Conversation {c.id}",
            "created_at": c.created_at.isoformat() if hasattr(c, 'created_at') else None
        } for c in conversations
    ]

@api_router.get("/conversation/{conversation_id}")
def get_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    conv = db.query(models.Conversation).filter(models.Conversation.iddd == conversation_id, models.Conversation.user_id == current_user.id).first()

    if not conv:
        return JSONResponse(status_code=403, content=classify_failure("UNAUTHORIZED_ACCESS", "Acces denied."))
    
    messages = db.query(models.Message).filter(models.Message.conversation_id == conversation_id).order_by(models.Message.created_at.asc()).all()

    return [
        {
            "role": msg.role.lower(),
            "content": msg.content,
            "timestamp": msg.created_at.isoformat() if hasattr(msg, 'created_at') else None
        } for msg in messages
    ]

@api_router.delete("/conversaation/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    conv = db.query(models.Conversation).filter(models.Conversation.user_id == current_user.id, models.Conversation.id == conversation_id).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    db.delete(conv)
    db.commit()
    return {"message": "Conversation deleted successfully!"}

@api_router.patch("/conversation/{conversation_id}")
def update_title(conversation_id: int, title: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    validate_input(title)

    conv = db.query(models.Conversation).filter(models.Conversation.user_id == current_user.id, models.Conversation.id == conversation_id).first()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversataion not found")
    
    conv.title = title
    db.commit()
    return {'title': conv.title, "id": conversation_id}

#Chat Streaming
@api_router.post("/chat-stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        validate_input(request.message)
    
    except Exception as e:
        return JSONResponse(status_code=403, content=classify_failure("UNAUTHORIZED_ACCESS", detail=str(e)))
    
    if not request.conversation_id or request.conversation_id == "null":
        temp_title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        new_conv = models.Conversation(title=temp_title, user_id=current_user.id)
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        conv_id = new_conv.id

    else:
        conv_id = int(request.conversation_id)

    chat_service.save_message(db, conv_id, "user", request.message)

    process_chat_task.delay(conv_id, current_user.id, request.message)

    async def stream_generator():
        pubsub = r_client.pubsub()
        channel = f"chat_stream_{conv_id}"
        pubsub.subscribe(channel)

        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message is not None:
                    token = message['data']
                    if token == b'[DONE]' or token == '[DONE]':
                        break

                    if isinstance(token, bytes):
                        token = token.decode('utf-8')
                    
                    yield f"data: {json.dumps({'payload': token})}\n\n"

                await asyncio.sleep(0.5)
        
        except Exception as e:
            print(f"Ran into issue, issue:{str(e)}")

        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

#Mission & Planning Routes

@api_router.get("/tasks")
def get_tasks(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Tasks).filter(models.Tasks.user_id == current_user.id, models.Tasks.id == task_id).first()

@api_router.delete("/task/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = db.query(models.Tasks).filter(models.Tasks.user_id == current_user.id, models.Tasks.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

@api_router.patch("/task/{task_id}")
def update_task_status(task_id: int, data: StatusUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = db.query(models.Tasks).filter(models.Tasks.user_id == current_user.id, models.Tasks.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task Not Found")
    
    task.status = data.status
    db.commit()
    return {"status": task.status}

@api_router.post("/plan")
async def create_execution_plan(request: PlanRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        validate_input(request.task)
    except Exception as e:
        return JSONResponse(status_code=403, content=classify_failure("UNAUTHORIZED_ACCESS", detail=str(e)))
    
    process_plan_task.delay(request.task, request.time_budget, request.mode, current_user.id)

    async def plan_generator():
        pubsub = r_client.pubsub()
        channel = f"plan_result_{current_user.id}"
        pubsub.subscribe(channel)
        try:
            yield f"data: {json.dumps({'status': 'initializing', 'message': 'Generating mission strategy...'})}\n\n"
            start_wait = time.time()
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is not None:
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                
                    yield f"data: {data}\n\n"
                    break

                if time.time() - start_wait > 300:
                    yield f"data: {json.dumps({'status': 'error', 'message': 'Plan generation timed out'})}\n\n"
                    break

                await asyncio.sleep(0.1)

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': 'Plan generation timed out'})}\n\n"
        
        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()

    return StreamingResponse(plan_generator(), media_type="text/event-stream")

#Execution & Telemetry
@api_router.post("/execute/{mission_id}")
async def start_execution(mission_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = db.query(models.Tasks).filter(models.Tasks.id == mission_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    if task.user_id != current_user.id:
        return JSONResponse(status_code=403, content=classify_failure("UNAUTHORIZED_ACCESS", detail="Mission ownership mismatch."))
    
    if task.status == "running":
        return {"status": "ALREADY_RUNNING", "message": "Agent is currently operating this mission."}
    
    steps = db.query(models.TaskStep).filter(models.TaskStep.task_id == mission_id).all()
    manifest = [
        {
            "backend_step_id": s.backend_step_id,
            "description": s.description,
            "time_allocated": s.time_allocated,
            "tool_required": s.tool_required,
            "logic_reasoning": s.logic_reasoning
        } for s in steps
    ]

    task_id = trigger_mission_execution(db, mission_id, task.total_time, manifest)
    r_client.hset(f"mission_meta:{mission_id}", "active_celery_id", task_id)

    return {"status": "QUEUED", "celery_task_id": task_id}

@api_router.get("/execute/{mission_id}")
async def get_live_mission_progress(mission_id: int, db: Session=Depends(get_db), current_user: models.User = Depends(get_current_user)):
    task = db.query(models.Tasks).filter(models.Tasks.id == mission_id, models.Tasks.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    celery_id = r_client.hget(f"mission_meta:{mission_id}", "active_celery_id")
    if celery_id:
        if isinstance(celery_id, bytes):
            celery_id = celery_id.decode('utf-8')

        task_result = celery.AsyncResult(celery_id)
        state = task_result.state
        progress_data = task_result.info if isinstance(task_result.info, dict) else {"message": str(task_result.info)}

    else:     
        state="PENDING"
        progress_data = {"message": "Waiting for worker to start."}

    steps = db.query(models.TaskStep).filter(models.TaskStep.task_id == mission_id).order_by(models.TaskStep.order).all()
    
    return {
        "mission_id": mission_id,
        "state": state,
        "status": task.status,
        "data": progress_data,
        "steps": [
            {
                "backend_step_id": s.backend_step_id,
                "description": s.description,
                "status": s.status,
                "tool_required": s.tool_required,
                "logic_reasoning": s.logic_reasoning
            } for s in steps
        ]
    }

@api_router.patch("/execute/{mission_id}/approve")
async def approve_mission_step(mission_id: int, data: StepApprovalRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    step_id = str(data.step_id)

    try:
        if data.description:
            validate_input(data.description)

    except Exception as e:
        return JSONResponse(status_code=403, content=classify_failure("UNAUTHORIZED_ACCESS", detail=str(e)))
    
    step_db = db.query(models.TaskStep).filter(models.TaskStep.task_id == mission_id, models.TaskStep.backend_step_id == step_id).first()

    if step_id:
        step_db.status = data.status
        if data.description: 
            step_db.description = data.description
        db.commit()

    approval_channel = f"mission_control_{mission_id}"
    payload = json.dumps({"action": "RESUME", "step_id": data.step_id})
    r_client.publish(approval_channel, payload)

    return {"status": "Step Approved", "mission_id": mission_id}

@api_router.post("/execute/cancel/{task_id}")
async def cancel_mission_execution(task_id: str):
    try:
        celery.control.revoke(task_id, terminate=True, signal="SIGKILL")
        return {"status": "success", "message": f"Termination Signal sent to {task_id}"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to issue kill command: {str(e)}")
    
#Vault and memory routes
@api_router.get("/memories")
def read_memories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return get_memories(db, current_user.id)

@api_router.post("/memory")
def add_user_memory(request: MemoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    try:
        validate_input(request.fact_key)
        validate_input(request.fact_value)

    except Exception as e:
        return JSONResponse(status_code=403, content=classify_failure("UNAUTHORIZED_ACCESS", detail=str(e)))
    
    return add_memory(db, user_id=current_user.id, fact_key=request.fact_key, fact_value=request.fact_value, importance=request.importance, category=request.category)

@api_router.delete("/memory/{memory_id}")
def delete_user_memory(memory_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    success = delete_memory(db, current_user.id, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return {"message": "Memory purged Successfully!"}

@api_router.patch("/memory/{memory_id}")
def update_user_memory(memory_id: int, updates: MemoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    updated = update_memory(db, user_id=current_user.id, memory_id=memory_id, updates=updates.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Memory not found")
    return updated

@api_router.post("/upload-doc")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    contents = await file.read()
    doc = fitz.open(stream=contents, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)

    result = save_and_ingest_document(db, title=file.filename, raw_text=full_text, user_id=current_user.id, file_path=file.filename)
    return {"message": "Document ingested successfully!", "details": result}

@api_router.get("/system/stats")
def get_stats(current_user: models.User = Depends(get_current_user)):
    return analytics_engine

@api_router.post("/mission/{mission_id}/archive-logs")
async def archive_logs(mission_id: int, data: dict):
    log_dir = "logs/missions"
    os.makedirs(log_dir, exist_ok=True)
    file_path = f"{log_dir}/mission_{mission_id}.txt"
    with open(file_path, "a") as f:
        f.write(f"\n--- SESSION ARCHIVE: {time.ctime()} ---\n{data.get('terminal_output','')}\n--- END OF SESSION ---\n")
    
    return {"status": "archived", "path": file_path}