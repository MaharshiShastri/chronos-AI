from sqlalchemy.orm import Session
from app.models import models

def get_or_create_conversation(db: Session, user_id: int, conversation_id: int = None, first_msg: str = ""):
    if conversation_id:
        conv = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
        if conv: return conv
    
    new_conv = models.Conversation(user_id=user_id, title=first_msg[:30])
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return new_conv

def build_chat_history(db: Session, conversation_id: int, limit=6):
    messages = db.query(models.Message).filter(
        models.Message.conversation_id == conversation_id
    ).order_by(models.Message.timestamp.desc()).limit(limit).all()
    
    history_txt = ""
    for msg in reversed(messages):
        role = "User" if msg.role == "user" else "AI"
        history_txt += f"{role}: {msg.content}\n"
    return history_txt + "AI:"

def save_message(db: Session, conversation_id: int, role: str, content: str):
    msg = models.Message(conversation_id=conversation_id, role=role, content=content)
    db.add(msg)
    db.commit()
    return msg