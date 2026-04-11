from sqlalchemy.orm import Session
from app.rag.embedder import rag_embedder
from app.rag.vector_store import rag_vector_store
from app.models.models import DocumentChunk
import numpy as np
from sentence_transformers import CrossEncoder

class Retriever:
    def __init__(self, k=15, final_k=3, threshold=2.0):
        self.k = k
        self.final_k = final_k
        self.threshold = threshold 
        self.rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def retrieve_context(self, query: str, db: Session):
        # 1. Generate and Flatten Embeddings
        query_embeddings = rag_embedder.generate_embeddings(query)
        query_selector = query_embeddings[0] if query_embeddings.ndim > 1 else query_embeddings
        
        # 2. FAISS Search
        distances, indices = rag_vector_store.search(query_selector, k=self.k)

        # 3. Filter valid FAISS hits
        valid_indices = []
        for dist, idx in zip(distances, indices):
            if idx != -1 and dist < 1e30: 
                if dist <= self.threshold:
                    valid_indices.append(int(idx))
        
        if not valid_indices:
            return []

        # 4. Fetch and Re-rank
        chunks = db.query(DocumentChunk).filter(DocumentChunk.vector_id.in_(valid_indices)).all()
        if not chunks: return []

        pairs = [[query, chunk.content] for chunk in chunks]
        scores = self.rerank_model.predict(pairs)

        scored_chunks = []
        for i, chunk in enumerate(chunks):
            scored_chunks.append({"content": chunk.content, "score": scores[i]})

        # Sort by Cross-Encoder score (highest first)
        top_ranked = sorted(scored_chunks, key=lambda x: x["score"], reverse=True)

        # 5. Final Selection Logic
        final_context = [
            c['content'] for c in top_ranked[:self.final_k]
            if c['score'] > -2.0 # Slightly more lenient than 0 for short queries
        ]

        print(f"DEBUG: Top Re-rank Score: {top_ranked[0]['score'] if top_ranked else 'N/A'}")
        return final_context

rag_retriever = Retriever()
