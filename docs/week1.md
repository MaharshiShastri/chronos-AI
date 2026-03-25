## Day 1
- Set up local LLM using Ollama (TinyLlama)
- Built initial Python inference script
- Tested basic prompt-response pipeline

## Day 2
- Created FastAPI backend
- Implemented basic `/chat` endpoint
- Added request/response schemas
- Integrated Ollama API (non-streaming)

## Day 3
- Added streaming support from Ollama
- Implemented token-based response streaming
- Improved error handling in AI service
- Removed basic blocking response flow

## Day 4
- Integrated PostgreSQL database
- Designed models: User, Conversation, Message
- Added conversation-based memory system
- Stored chat history in DB

## Day 5
- Built basic frontend (HTML, CSS, JS)
- Implemented chat UI and message rendering
- Connected frontend with backend APIs
- Added streaming UI rendering

## Day 6
- Implemented JWT authentication (signup/login)
- Added password hashing (Argon2)
- Secured endpoints with user validation
- Linked conversations to authenticated users
- Removed temporary hardcoded user handling

## Day 7
- Refactored project into `/backend` and `/frontend`
- Enhanced streaming using SSE format
- Added stop-generation feature (AbortController)
- Improved UI with loader animations and transitions
- Introduced session handling and localStorage persistence
- Added sidebar structure for chat sessions (initial version)
