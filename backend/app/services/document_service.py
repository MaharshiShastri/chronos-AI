import os
from sqlalchemy.orm import Session
from app.models import models
from app.rag.chunker import rag_chunker
from app.rag.vector_store import rag_vector_store
from app.rag.embedder import rag_embedder

def list_user_documents(db: Session, user_id: int):
    return db.query(models.Document).filter(models.Document.user_id == user_id).all()

def save_and_ingest_document(db: Session, title: str, raw_text: str, user_id: int, file_path: str=None) -> dict:
    final_path = file_path if file_path else f"/{user_id}/internal/document"

    new_doc = models.Document(filename=title, user_id=user_id, file_path=final_path)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    text_chunks = rag_chunker.create_chunks(raw_text)
    if not text_chunks:
        return {"document_id": new_doc.id, "chunks_count": 0}
    
    text_embeddings = rag_embedder.generate_embeddings(text_chunks)

    start_vector_id = rag_vector_store.add_to_index(text_embeddings)

    chunk_objects =  []
    for i, content in enumerate(text_chunks):
        chunk = models.DocumentChunk(
            document_id=new_doc.id,
            content=content,
            chunk_index=i,
            vector_id=start_vector_id + i
        )
        chunk_objects.append(chunk)

        db.bulk_save_objects(chunk_objects)
        db.commit()

        return {"document_id": new_doc.id, "chunks_count": len(text_chunks)}
    
    def remove_user_document(db: Session, user_id: int, document_id: int) -> bool:
        doc = db.query(models.Document).filter(
            models.Document.id == document_id,
            models.Document.user_id == user_id
        ).first()

        if not doc:
            return False
        
        db.query(models.DocumentChunk).filter(models.DocumentChunk.document_id == document_id).delete()
        db.delete(doc)
        db.commit()
        return True
    
    
    