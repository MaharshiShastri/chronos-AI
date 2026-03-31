### 📅 Day 1 — Time-Aware Planner Design
* **Redesigned Planning Engine**: Enforced strict JSON output format for LLM responses.
* **SSE Integration**: Introduced streaming plan generation via the `/plan` endpoint.
* **Structured Constraints**: Limited LLM output to `step` and `time_allocated` only.
* **Prompt Reliability**: Improved consistency using an instruction-wrapped format.
* **Frontend Logic**:
    * Added parsing strategies for partial JSON streams.
    * Introduced a **Plan Normalization Layer** to handle and fix malformed AI output.
* **Robustness**: Improved system resilience against LLM inconsistencies and token streaming gaps.

---

### 📅 Day 2 — Planner API + Time Input
* **Backend API**: Integrated time-budget-based planning logic.
* **Time Constraints**: Enabled user-controlled time limits for task execution.
* **Data Modeling**: 
    * Introduced the `Tasks` model for objective logging.
    * Built the `/tasks` endpoint for persistent storage.
* **UI/UX**: Connected the Plan Architect UI to the streaming `/plan` endpoint.
* **Execution Modes**: Added **Fast** and **Deep** modes for adaptive planning.
* **Refactoring**: Standardized streaming architecture across both Chat and Plan endpoints.

---

### 📅 Day 3 — Time-Aware Execution Engine
**🎯 Objective:** Transform static plans into a controlled execution system with real-time constraint enforcement.

* **Time-Constrained Executor**:
    * Tracks global start time and iterates through steps with strict checks.
    * Implemented step-level timeout handling and early stopping.
* **Backend Enhancements**:
    * Extended `/plan` to store tasks and steps with unique `step_id`.
    * Robust JSON extraction using regex fallbacks for noisy LLM outputs.
* **Reliability**: Improved Ollama integration with automated restart logic and empty response handling.
* **✅ Outcome**: A system that converts a task into a structured, persisted, and executable plan.

---

### 📅 Day 4 — Frontend Time Visualization & Streaming
**🎯 Objective:** Visualize execution in a way that feels real-time, controlled, and measurable.

* **ExecutionView UI**:
    * Step-by-step interface with dynamic highlighting for Active, Completed, and Timeout states.
    * Built-in **Countdown timers** per step and **Pause/Resume** functionality.
* **Streaming AI (SSE)**:
    * Implemented `/chat-stream` for token-level rendering.
    * Built a conversation memory system (fetches last 6 messages for context).
* **Security**:
    * Implemented **JWT-based authentication** middleware.
    * Fixed conversation ownership and session tracking logic.
* **🧠 Key Insight**: Shifted from request-response AI to a real-time interactive system—the foundation for agentic behavior.

---

### 📅 Day 5 — Plan Generation Engine (Structured Execution)
**🎯 Objective:** Transition from generating text to generating enforceable logic.

* **Logic Design**:
    * Strict constraints: 5–7 steps per plan.
    * Time normalization: Ensures the sum of steps equals the total user budget.
* **Database Models**:
    * Utilized `Tasks` and `TaskStep` for ordered execution tracking.
* **Frontend**: 
    * Built the **Plan Architect UI** featuring a time slider (60–3600s).
    * Added an **Objectives Log** sidebar to track all generated missions.
* **🧠 Key Insight**: AI is now a Decision Engine, not just a Chatbot.

---

### 📅 Day 6 — Agent Execution Engine + Human-in-the-Loop
**🎯 Objective:** Create a closed-loop execution system with human oversight.

* **Event-Driven Architecture**:
    * Backend emits events: `STEP_STARTED`, `REQUIRE_APPROVAL`, `STEP_COMPLETED`.
    * Implemented a **Drift Correction Algorithm** to redistribute time dynamically.
* **Human-in-the-Loop (HITL)**:
    * Created `pending_approvals` queue with async blocking via `asyncio.Event`.
    * Added `/approve` endpoint to resume execution after user feedback.
* **Real-Time Progress**:
    * Live SSE event handling on the frontend.
    * Visual drift warnings and countdowns for active mission monitoring.
* **🧠 Key Insight**: The system has evolved into an autonomous execution engine with strategic human control.
