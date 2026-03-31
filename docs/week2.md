## Week 2
---
### Day 1: Time-Aware Planner Design
- Redesigned planning engine to enforce strict JSON output format
- Introduced streaming plan generation (SSE-based `/plan` endpoint)
- Added structured constraints for LLM (step + time_allocated only)
- Improved prompt reliability using instruction-wrapped format
- Enabled real-time token streaming for plan construction
- Added frontend parsing strategy for partial JSON streams
- Introduced plan normalization layer (handles malformed AI output)
- Improved system robustness against LLM inconsistencies

### Day 2: Planner API + Time Input
- Integrated time-budget-based planning into backend API
- Enabled user-controlled time constraints for task execution
- Connected frontend plan architect UI to streaming `/plan` endpoint
- Added fast/deep execution modes for adaptive planning
- Introduced task tracking system (`Tasks` model)
- Built `/tasks` endpoint for objective logging
- Connected generated plans to persistent task storage
- Improved conversation-title handling and session tracking
- Refactored streaming architecture for both chat and plan endpoints
  ### 📅 Day 3 — Time-Aware Execution Engine
🎯 Objective

Transform static plans into a controlled execution system with real-time time awareness and constraint enforcement.

🧠 Key Concepts Learned
Execution control flow design
Time tracking in Python (datetime, timers)
Streaming + async coordination
Handling partial execution under constraints
🛠 Implementation
Built a Time-Constrained Executor logic:
Tracks global start time
Iterates through steps with strict time checks
Integrated:
Step-level timeout handling
Early stopping when time expires
Partial execution support
⚙️ Backend Enhancements
Extended /plan endpoint:
Stores tasks and generated steps in DB
Assigns unique step_id to each step
Implemented:
Streaming plan parsing with fallback logic
Robust JSON extraction from LLM output
Improved:
Ollama reliability (handling empty responses + restart logic)
🚧 Challenges Faced
LLM returning malformed JSON → solved using regex fallback parsing
Streaming inconsistencies → handled via buffer accumulation
Ensuring total time consistency across steps
✅ Outcome

A working backend system that:

Converts a task → structured execution plan
Persists it → prepares it for real-time execution
📅 Day 4 — Frontend Time Visualization
🎯 Objective

Visualize execution in a way that feels real-time, controlled, and measurable

🧠 Key Concepts Learned
UI state synchronization with streaming data
Timer-based UI updates using useEffect
Progress visualization patterns
🛠 Implementation
Execution UI (ExecutionView)
Step-by-step execution interface
Dynamic highlighting:
Active step
Completed steps
Timeout state
Time Features
⏱ Countdown timer per step
⏸ Pause / Resume functionality
⚠ Timeout indication (visual alert)
Progress Tracking
📊 Progress bar (based on steps completed)
📈 Percentage completion indicator
Plan Integration
Connected streaming /plan API to UI
Real-time plan rendering as steps arrive
Normalized plan structure for robustness
🎨 UI/UX Enhancements
Neumorphic design consistency
Animated transitions for active steps
Clear separation:
Chat mode
Planning mode
Execution mode
🚧 Challenges Faced
Streaming plan not arriving as clean structure → required normalization
Syncing timer with step changes
Handling empty/loading states during plan generation
✅ Outcome

A fully interactive execution system where:

Plans are not just generated
They are experienced, tracked, and controlled in real time

Day 4 – Streaming Execution Engine (SSE + Backend Flow)
Implemented real-time execution engine using Server-Sent Events (SSE) in FastAPI
Designed /execute/{mission_id} endpoint to stream step-by-step execution updates
Built async run_mission_stream() to simulate agent behavior under time constraints
Introduced structured execution events:
STEP_STARTED
REQUIRE_APPROVAL
STEP_COMPLETED
MISSION_COMPLETED
Created pending_approvals system using asyncio.Event for human-in-the-loop control
Ensured cleanup of pending states after mission completion
Day 5 – Human-in-the-Loop + Time Intelligence
Implemented approval workflow via /execute/{mission_id}/approve endpoint
Enabled two decision paths:
Approved → continue execution
Refined → update artifact dynamically
Built drift detection system:
Measured difference between allocated vs actual execution time
Developed TimeOptimizer to redistribute time dynamically across remaining steps
Ensured minimum time constraints per step to avoid collapse of plan
Integrated feedback loop between execution engine and optimizer
Day 6 – Frontend Execution UI + State Sync
Built ExecutionView.jsx for real-time mission visualization
Implemented:
Live progress tracking
Step highlighting (active/completed/pending)
Countdown timer per step
Integrated SSE stream with frontend using fetchStream()
Designed approval UI:
Editable artifact textarea
Approve / Refine actions
Synced backend events with UI states (STEP_STARTED, REQUIRE_APPROVAL, etc.)
Added mission lifecycle control:
Start execution
Pause on approval
Resume after decision
Implemented dynamic progress bar and completion trigger
