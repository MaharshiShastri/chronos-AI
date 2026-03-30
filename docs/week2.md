## Week 2
---
### Day 1
- Upgraded LLM model to `llama3.2:3b`
- Added GPU control via `CUDA_VISIBLE_DEVICES`
- Introduced `generate_plan()` for time-based task planning
- Created `/plan` endpoint for structured execution plans
- Added new schemas: `PlanRequest`, `PlanResponse`, `PlanStep`
- Enabled JSON-formatted AI outputs for planning
- Improved backend modularity for agent-like features
### Day 2
- Replaced entire frontend architecture with advanced UI system
- Implemented **Chronos Auth UI** with login/signup flow
- Built **ChatWindow with real-time streaming interaction**
- Added **Plan Architect system (time-budget + fast/deep modes)**
- Introduced **ExecutionView (step-by-step task execution UI)**
- Implemented **conversation archive system (rename/delete sessions)**
- Added **Objectives Log (task tracking dashboard)**
- Built **Neumorphic design system for UI consistency**
- Integrated **ShatterCube transition animation (state switching UX)**
- Added **custom streaming handler (SSE parsing on frontend)**
- Improved **plan normalization logic for robustness**
- Refactored API service layer for modularity
- Cleaned old frontend and fully replaced with new system
