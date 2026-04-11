from sqlalchemy.orm import Session
from app.rag.embedder import rag_embedder
from app.rag.vector_store import rag_vector_store
from app.models.models import DocumentChunk
import numpy as np
from sentence_transformers import CrossEncoder
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch

class Retriever:
    def __init__(self, k=15, final_k=3, threshold=2.0): # Relaxed initial threshold
        self.k = k
        self.final_k = final_k
        self.threshold = threshold 
        self.rerank_model = CrossEncoder("./models/re-ranker")
        self.rerank_model.save("./models/re-ranker")
        self.summarizer_tokenizer = AutoTokenizer.from_pretrained('./models/summarizer')
        self.summarizer_model = AutoModelForSeq2SeqLM.from_pretrained('./models/summarizer')
        self.summarizer_model.save_pretrained("./models/summarizer")
        self.summarizer_tokenizer.save_pretrained("./models/summarizer")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print("Running Torch on: ", self.device)
        self.summarizer_model.to(self.device)


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

        compressed_context = self.compress_context(query, final_context)

        return compressed_context

    def compress_context(self, query: str, chunks: list):
        unique_chunks = list(dict.fromkeys(chunks))
        compressed_segments = []
        for chunk in unique_chunks:
            if(len(chunk.split()) > 50):
                try:
                    
                    input_text = f"summarize: {chunk}"
                    print("Prompt: ", input_text)
                    inputs = self.summarizer_tokenizer.encode(
                        input_text,
                        return_tensors="pt",
                        max_length=512,
                        truncation=True
                    ).to(self.device)

                    summary_ids = self.summarizer_model.generate(
                        inputs,
                        max_length = 100,
                        min_length = 30,
                        length_penalty = 2.0,
                        num_beams = 4,
                        early_stopping = True
                    )

                    summary = self.summarizer_tokenzier.decode(
                        summary_ids[0],
                        skip_special_tokens=True
                    )

                    compressed_segments.append(summary)
                except Exception as e:
                    print(f"Summarization error: {e}")
                    compressed_segments.append(chunk)  # Fallback to original chunk if summarization fails
            else:
                compressed_segments.append(chunk)

        return compressed_segments

rag_retriever = Retriever()
