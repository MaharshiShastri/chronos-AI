from database import SessionLocal
from app.rag.retriever import rag_retriever

db = SessionLocal()

try:
    user_query = "C++"
    context_segments, metrics = rag_retriever.retrieve_context(user_query, db)

    print(f"Query: {user_query}")
    print(f"Retrieved {len(context_segments)} relevant segments.")
    print("RAG Retrieval Metrics:", metrics)
    for i in context_segments:
        print(i)  # Print first 100 chars

finally:
    db.close()