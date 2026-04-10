from sqlalchemy.orm import Session
from app.rag.embedder import rag_embedder
from app.rag.vector_store import rag_vector_store
from app.models.models import DocumentChunk
import numpy as np

class Retriever:
    def __init__(self, k=3, threshold=0.7):
        self.k = k
        self.threshold = threshold # Confidence level

    def retrieve_context(self, query: str, db: Session):
        query_embeddings = rag_embedder.generate_embeddings(query)
        
        # Normalize embedding dimension
        if isinstance(query_embeddings, np.ndarray) and query_embeddings.ndim > 1:
            query_selector = query_embeddings[0]
        else:
            query_selector = query_embeddings

        # FAISS returns distances and indices
        distances, indices = rag_vector_store.search(query_selector, k=self.k)

        # 1. FILTER BY CONFIDENCE
        # If using Cosine Similarity: valid = score >= threshold
        # If using L2 Distance: valid = score <= threshold (you'd need to tune this)
        valid_pairs = []
        for dist, idx in zip(distances, indices):
            if idx != -1 and dist <= self.threshold: # Assuming Cosine Similarity
                valid_pairs.append(int(idx))
            else:
                print(f"DEBUG: Dropping context with low confidence: {dist}")

        if not valid_pairs:
            print("DEBUG: No context met the confidence threshold.")
            return []
        
        # 2. FETCH FROM DB
        chunks = db.query(DocumentChunk).filter(DocumentChunk.vector_id.in_(valid_pairs)).all()

        seen_content = set()
        ordered_context = []
        chunk_map = {chunk.vector_id: chunk.content for chunk in chunks}

        # Maintain FAISS ordering (best match first)
        for idx in valid_pairs:
            if idx in chunk_map:
                content = chunk_map[idx]
                if content not in seen_content:
                    ordered_context.append(content)
                    seen_content.add(content)

        return ordered_context

# Increase threshold to be stricter (e.g., 0.75) 
# to keep your resume out of plumbing tasks.
rag_retriever = Retriever(k=3, threshold=0.75)