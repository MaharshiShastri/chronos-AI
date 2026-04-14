from fastapi import APIRouter, Depends, HTTPException, status, FastAPI, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse, JSONResponse
from jose import jwt, JWTError
import json
import asyncio
import fitz

# Internal Imports (User-defined modules and methods)
from database import SessionLocal
from app.schemas.schemas import ChatRequest, ChatResponse, UserAuth, PlanResponse, PlanRequest, StatusUpdate, MemoryCreate
from app.services.ai_service import generate_response, generate_stream, generate_plan
import app.models.models as models
from app.core.auth import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from app.services.executor import run_mission_stream, ACTIVE_MISSIONS
from fastapi.security import OAuth2PasswordBearer
from app.services import chat_service, task_service
from app.rag.retriever import rag_retriever
from app.rag.ingestor import ingest_text, get_grounded_context
from app.services.memory_service import get_memories, add_memory, delete_memory, update_memory, extract_and_save_memories

api_router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_rag_context(query: str, db: Session, threshold=0.7):
    try:
        result, metrics = rag_retriever.retrieve_context(query, db)
                
        if not result:
            return ""
        
        with open("retrieval_metrics.log", "a") as log_file:
            log_file.write(json.dumps(metrics) + "\n")
            print("RAG Retrieval Metrics:", metrics)
        context_block = "\n--- RELEVANT DOCUMENTS ---\n" + "\n".join(result)
        return context_block
    
    except Exception as e:
        print(f"RAG RETRIEVAL ERROR: {e}")
    return None

    
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
@api_router.post("/chat-stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user), bg_tasks: BackgroundTasks = BackgroundTasks()):
    
    if not current_user:
        raise HTTPException(status_code=401, detail="User session invalid")

    # 1. Handle Conversation Creation/Lookup
    if not request.conversation_id or request.conversation_id == "null":
        temp_title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        new_conv = models.Conversation(title=temp_title, user_id=current_user.id)
        db.add(new_conv)
        db.commit()
        db.refresh(new_conv)
        conv_id = new_conv.id
    else:
        conv_id = int(request.conversation_id)

    # 2. RETRIEVE CONTEXT 
    # Use the retriever as the single source for RAG context
    doc_context = get_rag_context(request.message, db)
    #print(doc_context[:10])

    # 3. Save User Message
    chat_service.save_message(db, conv_id, "user", request.message)
    
    # 4. Get User Memories
    memories = get_memories(db, current_user.id)
    memory_context = ""
    if memories:
        memory_context = "USER FACTS:\n" + "\n".join(
            [f"-[{m.category}] {m.fact_key}: {m.fact_value}" for m in memories if m.importance >= 3]
        )
        
    # 5. Build History
    history = chat_service.build_chat_history(db, conv_id)
    
    # 6. Construct Final Prompt (Unified Context)
    # We use doc_context here which contains the actual text from your PDF chunks
    full_prompt = f"""<|system|>
You are a specialized AI collaborator. Answer using the provided context.
If the information is not in the context, use your general knowledge but mention it.
Always cite your sources using [Filename] format.

{doc_context}
{memory_context}

--- RECENT CONVERSATION ---
{history[-5:]}

<|user|>
{request.message}
<|assistant|>"""

    print(f"Full prompt sent to model:\n{full_prompt}\n--- END OF PROMPT ---")

    async def stream_generator():
        ai_response = ""
        try:
            yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"
            for token in generate_stream(full_prompt):
                ai_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            chat_service.save_message(db, conv_id, "AI", ai_response)
            # Ingest for future turns AFTER the response is generated
            bg_tasks.add_task(ingest_text, db, f"Conversation {conv_id}", request.message, current_user.id, "conversation")

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
    return {"title": conv.title, "id": conversation_id}
#END of Ordinary conversations with AI functions below for web-equivalent CRUD operations
#START of Agentic AI with time-awareness engine conversations with functions below for web-equivalent CRUD operations
#Create function of web-equivalent method
@api_router.post("/plan")
async def create_execution_plan(request: PlanRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    raw_steps = []
        
    context = get_rag_context(request.task, db)
    task_input = request.task
    if context:
        task_input = (f"""
            TASK: {request.task}\n
            REFERENCE KNOWLEDGE FROM DOCUMENTS: {context}\n 
            INSTRUCTION: Use the reference knowledge to make the steps more specific.
            """)
    
    print(f"Task input to plan generator: {task_input}")  # Debug log to check the final input to the plan generator
    try:
        for step in generate_plan(task_input, request.time_budget, request.mode):
            print(type(step))
            if isinstance(step, str):
                step = {"step": step, "time_allocated": 60}
            
            if isinstance(step, dict) and "error" in step:
                return JSONResponse(status_code=500, content=step)
            
            raw_steps.append(step)
            print(raw_steps)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    if not raw_steps:
        return JSONResponse(status_code=400, content={"error": "PLAN_GENERATION_FAILED"})

    # 2. SAVE TO DB (Now we have the full list)
    mission_id, enriched = task_service.create_mission_and_steps(
        db, current_user.id, request.task, request.time_budget, raw_steps
    )
    ingest_text(db, title=f"Task {mission_id}", raw_text = request.task, user_id=current_user.id, source_type="task") #Ingest the task description into RAG system for future retrieval
    # 3. STREAM THE RESULTS TO UI
    async def plan_generator():
        try:
            # First, stream the steps for the "Loading" UI one by one
            for step_object in raw_steps:
                print(f"Streaming step: {step_object}")  # Debug log to see the step being streamed
                yield f"data: {json.dumps({'single_step': step_object, 'status': 'streaming'})}\n\n"
                await asyncio.sleep(0.1) # Tiny delay so the UI animation looks smooth

            # Finally, send the completion signal with the mission_id
            yield f"data: {json.dumps({
                'mission_id': mission_id, 
                'enriched_steps': enriched, 
                'status': 'complete'
            })}\n\n"
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
async def start_execution(mission_id: int, db: Session = Depends(get_db)):
    #Once the step is approved, execute it here, remove from current list of steps
    #Do this until the entire task list is completed

    task = db.query(models.Tasks).filter(models.Tasks.id == mission_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Mission not found")

    steps = db.query(models.TaskStep).filter(models.TaskStep.task_id == mission_id).all()
    manifest = [
        {
            "id": s.id,
            "backend_step_id": s.backend_step_id, # Changed from step_id
            "description": s.description, 
            "time_allocated": s.time_allocated,
            "status": "pending",
            "artifact_content": ""
        }
        for s in steps
    ]

    async def event_generator():
        try:
            yield f"data: {json.dumps({'event': 'MANIFEST', 'steps': manifest})}\n\n"

            async for event in run_mission_stream(mission_id, task.total_time, manifest):
                yield f"data: {json.dumps(event)}\n\n"

            for item in manifest:
                db.query(models.TaskStep).filter(
                        models.TaskStep.task_id == mission_id,
                        models.TaskStep.backend_step_id == item['backend_step_id']
                    ).update({
                        "status": item["status"],
                        "artifact_content": item["artifact_content"]
                    })
            db.commit()
            yield f"data: {json.dumps({'event': 'DB_SYNC_COMPLETE'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'ERROR', 'detail': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@api_router.patch("/execute/{mission_id}/approve")
async def approve_mission_step(mission_id: int, data: dict, db: Session = Depends(get_db)):
    step_id = str(data.get("step_id"))
    status_to_set = data.get("status", "completed")
    new_content = data.get("content")

    # 1. Update the LIVE manifest in memory first
    if mission_id in ACTIVE_MISSIONS:
        manifest = ACTIVE_MISSIONS[mission_id]
        # Find the specific step in the memory list
        step_in_memory = next((s for s in manifest if str(s.get('backend_step_id')) == step_id), None)
        
        if step_in_memory:
            step_in_memory['status'] = status_to_set
            if new_content:
                step_in_memory['artifact_content'] = new_content
            
            # 2. ALSO update DB in background so the state is persisted 
            # if the user refreshes the page
            step_db = db.query(models.TaskStep).filter(
                models.TaskStep.task_id == mission_id,
                models.TaskStep.backend_step_id == step_id
            ).first()
            
            if step_db:
                step_db.status = status_to_set
                if new_content:
                    step_db.artifact_content = new_content
                db.commit()
                
            return {"message": "Memory updated, stream will proceed."}

    raise HTTPException(status_code=404, detail="Mission not currently active in memory")

#End of Agentic AI with time-awareness engine conversations with functions below for web-equivalent CRUD operations
#START of Memory Vault functions for web-equivalent CRUD operations
@api_router.get("/memories")
def read_memories(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return get_memories(db, current_user.id)

@api_router.post("/memory")
def add_user_memory(request: MemoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    new_memory = add_memory(
        db,
        user_id = current_user.id,
        fact_key = request.fact_key,
        fact_value = request.fact_value,
        importance = request.importance,
        category = request.category
    )
    return new_memory

@api_router.delete("/memory/{memory_id}")
def delete_user_memory(memory_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    success = delete_memory(db, current_user.id, memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found or access denied")
    
    return {"message": "memory purged successfully!"}

@api_router.patch("/memory/{memory_id}")
def update_user_memory(memory_id: int, updates: MemoryCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    updated_memory = update_memory(
        db,
        user_id = current_user.id,
        memory_id = memory_id,
        updates = updates.dict(exclude_unset=True)
    )
    if not updated_memory:
        raise HTTPException(status_code=404, detail="Memory not found or access denied")
    
    return updated_memory


@api_router.post("/upload-doc")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    contents = await file.read()
    doc = fitz.open(stream=contents, filetype="pdf")

    full_text = ""
    for page in doc:
        full_text += page.get_text()

    result = ingest_text(db, title=file.filename, raw_text=full_text, user_id=current_user.id, source_type="pdf")

    return {"message": "Document ingested successfully!", "details": result}
