from backend.database import SessionLocal
from retriever import rag_retriever

db = SessionLocal()

try:
    user_query = "How does environment shape behaviour?"
    context_segments = rag_retriever.retrieve_context(user_query, db)

    print(f"Query: {user_query}")
    print(f"Retrieved {len(context_segments)} relevant segments.")
    for i, txt in context_segments:
        print(f"--- \t Context: {i+1} ---\n{txt[:200]}...")

finally:
    db.close()