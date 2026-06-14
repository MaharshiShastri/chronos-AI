@echo off
echo ==================================================
echo   LAUNCHING CHRONOS DEVELOPMENT ENVIRONMENT
echo ==================================================

:: Give Redis 2 seconds to warm up before workers connect
timeout /t 2 /nobreak > nul

:: 2. Start Uvicorn backend
echo Starting FastAPI Backend...
start "FastAPI Backend" cmd /k "cd /d D:\full stack projects\local LLM\backend && uvicorn main:app --reload"


:: 3. Start celery worker
echo Starting Celery workers...
start "Celery Worker" cmd /k "cd /d D:\full stack projects\local LLM\backend && celery -A app.services.tasks worker -Q chat_queue,plan_queue -c 2 --loglevel=info -P solo"


:: 4. Start Frontend
echo starting Front-end
start "Vite Frontend" cmd /k "cd /d D:\full stack projects\local LLM\frontend && npm run dev"

echo All services dispatched! You can close this root terminal.
pause