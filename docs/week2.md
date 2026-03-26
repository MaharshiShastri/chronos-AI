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
