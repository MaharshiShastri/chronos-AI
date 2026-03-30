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
