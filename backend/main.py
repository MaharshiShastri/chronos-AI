from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from app.api import router_logic

app = FastAPI(title = "Mission-control Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5500", "http://localhost:5173"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

# WARNING: This deletes everything every time the server restarts!
# Useful only during heavy development/debugging, do not unnecessarily un-comment the next line.
#Base.metadata.drop_all(bind=engine) !!<- DO NOT UNCOMMENT UNLESS FORCED TO
Base.metadata.create_all(bind=engine)

app.include_router(router_logic.api_router) #Let the router file deal with routing to correct endpoint

if __name__ =="__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port = 8000)