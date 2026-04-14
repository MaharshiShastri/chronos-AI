from sqlalchemy.orm import Session
from app.rag.embedder import rag_embedder
from app.rag.vector_store import rag_vector_store
from app.models.models import DocumentChunk, Document
import numpy as np
from sentence_transformers import CrossEncoder
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch

from datetime import datetime, timezone
import time


class Retriever:
    def __init__(self, k=15, final_k=3, threshold=2.0): # Relaxed initial threshold
        self.k = k
        self.final_k = final_k
        self.threshold = threshold 
        self.rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        #self.rerank_model.save("./models/re-ranker")
        self.summarizer_tokenizer = AutoTokenizer.from_pretrained('t5-small')
        self.summarizer_model = AutoModelForSeq2SeqLM.from_pretrained('t5-small')
        #self.summarizer_model.save_pretrained("./models/summarizer")
        #self.summarizer_tokenizer.save_pretrained("./models/summarizer")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.summarizer_model.to(self.device)


    def retrieve_context(self, query: str, db: Session):
        # 1 & 2. Embeddings & FAISS Search (Keep your existing logic)
        start_time = time.perf_counter()
        query_embeddings = rag_embedder.generate_embeddings(query)
        query_selector = query_embeddings[0] if query_embeddings.ndim > 1 else query_embeddings
        distances, indices = rag_vector_store.search(query_selector, k=self.k)
        # Inside Retriever.__init__
        print(f"DEBUG: FAISS Index Count: {rag_vector_store.index.ntotal}")
        # 3. Filter valid FAISS hits
        valid_indices = [int(idx) for dist, idx in zip(distances, indices) 
                         if idx != -1 and dist < 1e30 and dist <= self.threshold]

        if not valid_indices: return []

        # 4. Day 3: FETCH WITH JOIN (Get the filename from the Document table)
        # We join DocumentChunk with Document to get the actual source name
        chunks_with_titles = (
            db.query(DocumentChunk, Document)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(DocumentChunk.vector_id.in_(valid_indices))
            .all()
        )
        #print(chunks_with_titles)
        if not chunks_with_titles: return []

        # 5. Day 1: RE-RANKING
        # chunks_with_titles is a list of tuples: (DocumentChunk object, "filename.pdf")
        pairs = [[query, item[0].content] for item in chunks_with_titles]
        scores = self.rerank_model.predict(pairs)

        scored_chunks = []
        now = datetime.now(timezone.utc)
        #print(pairs)
        for i, result in enumerate(chunks_with_titles):
            #Day 4: Recency vs Relevancy logic
            chunk_object = result[0]  # DocumentChunk object
            doc_object = result[1]

            semantic_score = scores[i]
            doc_date = doc_object.upload_date.replace(tzinfo=timezone.utc)
            delta_days = (now - doc_date).days
            recency_boost = 1.0 / (1.0 + (delta_days / 30))
            final_weighted_score = semantic_score + (recency_boost * 0.5) 

            scored_chunks.append({
                "content": chunk_object.content, 
                "score": final_weighted_score, 
                "source": doc_object.filename, # Use filename as the source,
                "date": doc_date
            })

        # Sort by Cross-Encoder score
        top_ranked = sorted(scored_chunks, key=lambda x: x["score"], reverse=True)

        # 6. DIVERSITY FILTER (Multi-Doc Logic)
        final_context = []
        seen_sources = {}

        for c in top_ranked:
            # Re-ranker scores for ms-marco are better > -1.0 for short queries
            if c["score"] < -1.0: continue 
            
            source = c["source"]
            # Logic: Pull max 2 chunks from any single file to force diversity
            if seen_sources.get(source, 0) < 2:
                # Add source metadata so the LLM knows where info came from
                context_entry = f"[{source}]: {c['content']}"
                final_context.append(context_entry)
                seen_sources[source] = seen_sources.get(source, 0) + 1

            if len(final_context) >= self.final_k:
                break
        end_time = time.perf_counter()
        metrics = {
            "retrieval_time": (end_time - start_time) * 1000,
            "chunks_found" : len(valid_indices),
            "final_chunks_used" : len(final_context),
            "top_score" : float(top_ranked[0]["score"]) if top_ranked else None 
        }

        # 7. COMPRESS
        return self.compress_context(final_context), metrics
    
    def compress_context(self, chunks: list):
        unique_chunks = list(dict.fromkeys(chunks))
        compressed_segments = []
        
        for chunk in unique_chunks:
            # 1. Extract the source tag (e.g., "[resume.pdf]")
            source_tag = ""
            actual_content = chunk
            if "]: " in chunk:
                source_tag, actual_content = chunk.split("]: ", 1)
                source_tag += "]: " # Re-add the formatting

            if len(actual_content.split()) > 50:
                try:
                    # 2. Summarize ONLY the actual content, not the metadata
                    input_text = f"summarize: {actual_content}"
                    inputs = self.summarizer_tokenizer.encode(
                        input_text, return_tensors="pt", max_length=512, truncation=True
                    ).to(self.device)

                    summary_ids = self.summarizer_model.generate(
                        inputs, max_length=100, min_length=30, length_penalty=2.0,
                        num_beams=4, early_stopping=True
                    )

                    summary = self.summarizer_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
                    
                    # 3. Re-attach the source tag to the summarized text
                    compressed_segments.append(f"{source_tag}{summary}")
                    
                except Exception as e:
                    print(f"Summarization error: {e}")
                    compressed_segments.append(chunk) 
            else:
                compressed_segments.append(chunk)
                
        return compressed_segments

rag_retriever = Retriever()
