from sqlalchemy.orm import Session
from app.models.models import UserMemory
from app.services.ai_service import generate_response

def get_memories(db: Session, user_id: int):
    return db.query(UserMemory).filter(UserMemory.user_id == user_id).all()

def add_memory(db:Session, user_id: int, fact_key: str, fact_value: str, importance: int=1, category: str="general"):
    db_memory = UserMemory(user_id=user_id, fact_key=fact_key, fact_value=fact_value, importance=importance, category=category)
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
    return db_memory

def delete_memory(db: Session, user_id: int, memory_id: int):
    memory = db.query(UserMemory).filter(UserMemory.user_id == user_id, UserMemory.id == memory_id).first()
    if memory:
        db.delete(memory)
        db.commit()
        return True
    return False

def update_memory(db: Session, user_id: int, memory_id: int, updates: dict):
    db_memory = db.query(UserMemory).filter(
        UserMemory.user_id == user_id, 
        UserMemory.id == memory_id
    ).first()
    
    if not db_memory:
        return None

    for key, value in updates.items():
        if hasattr(db_memory, key):
            setattr(db_memory, key, value)
            
    db.commit()
    db.refresh(db_memory)
    return db_memory

def extract_and_save_memories(user_input, ai_response, db: Session, user_id: int):
    # Placeholder for actual extraction logic
    extraction_prompt = f"""Analyze the following interaction. 
    If the user shared a permanent fact (identity, preference, skill, or goal), 
    extract it as a short, first-person fact (e.g., 'The user is a C++ expert').
    If no new info was shared, return 'NONE'.
    
    USER: {user_input}
    AI: {ai_response}"""

    extracted_facts = generate_response(extraction_prompt)  # This should return a list of fact dicts or 'NONE'
    for fact in extracted_facts:
        if fact == "NONE":
            break
        new_memory = UserMemory(fact_value=fact, user_id=user_id)
        db.add(new_memory)
        db.commit()


    