import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from database import SessionLocal
import app.models.models as models
from app.rag.ingestor import ingest_text

def run_repopulation():
    db: Session = SessionLocal()
    print("🚀 Starting RAG Repopulation (Fresh Start)...")
    
    try:
        # STEP 0: CLEAR OLD DATA (Optional but recommended for clean repopulation)
        # db.query(models.DocumentChunk).delete()
        # db.query(models.Document).delete()
        # db.commit()

        # 1. TASKS
        print("\n--- 📝 Indexing Tasks ---")
        tasks = db.query(models.Tasks).all()
        for t in tasks:
            # Aggregate task info
            steps_text = " ".join([f"Step: {s.description}" for s in t.steps])
            content = f"Task: {t.title}. Steps: {steps_text}"
            ingest_text(db, title=f"Task_{t.id}", raw_text=content, user_id=t.user_id, source_type="task")
            print(f"✅ Indexed Task {t.id}")

        # 2. MESSAGES
        print("\n--- 💬 Indexing Chat History ---")
        messages = db.query(models.Message).filter(models.Message.role == "user").all()
        for m in messages:
            # We get the user_id from the conversation
            conv = db.query(models.Conversation).filter(models.Conversation.id == m.conversation_id).first()
            if conv:
                ingest_text(db, title=f"Chat_{m.id}", raw_text=m.content, user_id=conv.user_id, source_type="chat")
                print(f"✅ Indexed Message {m.id}")

        # 3. MEMORY
        print("\n--- 🧠 Indexing Memory ---")
        memories = db.query(models.UserMemory).all()
        for mem in memories:
            content = f"User Fact: {mem.fact_key} is {mem.fact_value}"
            ingest_text(db, title=f"Mem_{mem.id}", raw_text=content, user_id=mem.user_id, source_type="memory")
            print(f"✅ Indexed Memory {mem.id}")

        # 4. PHYSICAL DOCUMENTS (The only ones needing real paths)
        # NOTE: Only run this if you have a local folder with the original files!
        # Otherwise, skip this section to avoid the 'DB_INTERNAL' error.

    except Exception as e:
        print(f"❌ ERROR: {e}")
        db.rollback()
    finally:
        db.close()
        
if __name__ == "__main__":
    print("!!! WARNING: Ensure you have truncated 'document_chunks' and 'documents' tables if you want a clean start.")
    print("!!! Ensure FAISS index file is deleted or cleared.")
    confirm = input("Proceed with full repopulation? (y/n): ")
    if confirm.lower() == 'y':
        run_repopulation()