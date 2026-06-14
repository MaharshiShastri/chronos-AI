import asyncio
import httpx
import time
import statistics
import os
import psutil
import matplotlib.pyplot as plt
import random
from tqdm import tqdm

# --- CONFIGURATION ---
BASE_URL = "http://localhost:8000"
MISSION_ID = 8
TIMESTAMP = int(time.time())
LOG_FILE = f"logs/prod_mirror_m{MISSION_ID}_{TIMESTAMP}.txt"
CHART_FILE = f"logs/prod_mirror_visual_{TIMESTAMP}.png"
MAX_CONCURRENT_TASKS = 2000

# MOCK CREDENTIALS (Ensure these exist in your local DB)
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYWhhcnNoaXNoYXN0cmkxMkBnbWFpbC5jb20iLCJleHAiOjE5MDA2MDExMzV9.VwiiNRVfY5YemKGaLoFGOXMVOlaQEfGSQTFVrMLmosM" 
HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}

os.makedirs("logs", exist_ok=True)

class AvalancheLogger:
    def __init__(self, filepath):
        self.file = open(filepath, "a", encoding="utf-8")
        self.cpu_usage = []
        self.mem_usage = []
    def log(self, message):
        print(message)
        self.file.write(message + "\n")
        self.file.flush()
    def record_vitals(self):
        self.cpu_usage.append(psutil.cpu_percent())
        self.mem_usage.append(psutil.virtual_memory().percent)
    def close(self):
        self.file.close()

logger = AvalancheLogger(LOG_FILE)

# --- REAL-WORLD PERSONAS ---

async def persona_chatter(stop_event):
    """Simulates 'The Socialite': Users constantly streaming chat messages."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=210.0) as client:
        while not stop_event.is_set():
            try:
                # Mirroring /chat-stream logic
                payload = {"message": "Give me more details about this mission", "conversation_id": 1}
                async with client.stream("POST", f"{BASE_URL}/chat-stream", json=payload) as resp:
                    if resp.status_code == 422:
                        # Log the detail to see exactly what Pydantic hates
                        print(f"DEBUG 422: {resp.json()}") 
                        pass
                    async for _ in resp.aiter_lines(): pass 
                await asyncio.sleep(random.uniform(1, 3))
            except Exception:
                await asyncio.sleep(1)

async def persona_intern(stop_event):
    """Simulates 'The Intern': Users managing memories and small uploads."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        while not stop_event.is_set():
            try:
                # Testing Memory CRUD & Retrieval
                await client.get(f"{BASE_URL}/memories")
                if random.random() > 0.7:
                    await client.post(f"{BASE_URL}/memory", json={"content": "Log: System stable", "category": "status"})
                await asyncio.sleep(random.uniform(2, 5))
            except Exception:
                await asyncio.sleep(1)

async def simulate_executor(user_id, start_ts, queue):
    """'The Worker': Mirroring your frontend executeMission + approveStep logic."""
    url = f"{BASE_URL}/execute/{MISSION_ID}"
    try:
        async with httpx.AsyncClient(timeout=210, headers=HEADERS) as client:
            async with client.stream("GET", url) as response:
                if response.status_code == 200:
                    async for line in response.aiter_lines():
                        if "REQUIRE_APPROVAL" in line:
                            # Mirroring approveStep call
                            try:
                                await client.patch(f"{BASE_URL}/execute/{MISSION_ID}/approve", 
                                                json={"step_id": "STP-B5781E", "status": "approved", "content": "Auto-Approved by Stress Test"})
                            except Exception as e:
                                logger.log(f"⚠️ Approval failed for {user_id}: {str(e)[:20]}")
                    
                    
                    end_ts = time.time() - start_ts
                    for i in range(2):
                        queue.put_nowait(simulate_executor(f"{user_id}.{i+1}", start_ts, queue))
                    return {"id": user_id, "success": True, "duration": round(end_ts, 2), "end_ts": end_ts}
                else:
                    return {"id": user_id, "success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"id": user_id, "success": False, "error": str(e)[:20]}

# --- AUDIT DASHBOARD ---

def save_audit_dashboard(results, user_count, cpu_data, mem_data):
    successes = [r for r in results if r['success']]
    durations = [r['duration'] for r in successes]
    completion_timeline = sorted([(r['end_ts'], r['id']) for r in successes])
    times, _ = zip(*completion_timeline) if completion_timeline else ([], [])

    plt.style.use('dark_background')
    fig, axs = plt.subplots(2, 2, figsize=(18, 10))
    
    axs[0, 0].plot(times, range(1, len(times) + 1), color='#00ffcc', linewidth=2)
    axs[0, 0].set_title("Success Timeline (Mixed Payload)")

    axs[0, 1].plot(cpu_data, label="CPU %", color='#ff3333')
    axs[0, 1].plot(mem_data, label="RAM %", color='#3399ff')
    axs[0, 1].set_title("Auth & Logic Hardware Impact")
    axs[0, 1].legend()

    axs[1, 0].hist(durations, bins=25, color='#00ffcc', alpha=0.6)
    axs[1, 0].set_title("Latency (Chat + Exec + Memory)")

    axs[1, 1].axis('off')
    stats_text = (
        f"--- PRODUCTION MIRROR AUDIT ---\n"
        f"Breaking Point: {user_count} total requests\n"
        f"P99 Latency: {round(max(durations), 2) if durations else 0}s\n"
        f"Peak CPU: {max(cpu_data) if cpu_data else 0}%\n"
        f"Active Endpoints: /execute, /chat-stream, /memory\n"
        f"Auth Status: JWT Validation Active"
    )
    axs[1, 1].text(0.1, 0.5, stats_text, fontsize=14, family='monospace', verticalalignment='center')

    plt.tight_layout()
    plt.savefig(CHART_FILE)
    print(f"📊 Production-Mirror Dashboard saved: {CHART_FILE}")

# --- ORCHESTRATION ---
async def monitor_hardware(stop_event):
    """Background task to poll hardware metrics every half second."""
    while not stop_event.is_set():
        logger.record_vitals()
        await asyncio.sleep(0.5)


async def run_mirror_test(initial_executors=50):
    logger.log(f"🚀 STARTING MIRROR TEST: Auth + Multi-Endpoint Pressure")
    start_ts = time.time()
    stop_event = asyncio.Event()
    queue = asyncio.Queue()
    results = []
    
    # 1. Start Hardware Monitor
    monitor_task = asyncio.create_task(monitor_hardware(stop_event)) # Simplified representation
    # (Actually uses the proper monitor_hardware function from previous context)

    # 2. Launch Diversified Background Noise
    noise_tasks = [
        *[asyncio.create_task(persona_chatter(stop_event)) for _ in range(10)],
        *[asyncio.create_task(persona_intern(stop_event)) for _ in range(5)]
    ]

    for i in range(initial_executors):
        queue.put_nowait(simulate_executor(str(i), start_ts, queue))

    pbar = tqdm(desc="System Load", unit="req")
    active_tasks = set()
    system_broken = False

    while not queue.empty() or active_tasks:
        while not queue.empty() and len(active_tasks) < MAX_CONCURRENT_TASKS:
            active_tasks.add(asyncio.create_task(queue.get_nowait()))
        
        if not active_tasks: break
        done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
        
        for task in done:
            res = await task
            results.append(res); pbar.update(1)
            if not res['success']:
                logger.log(f"💥 FAILURE at req {len(results)}: {res.get('error')}")
                system_broken = True; break
        if system_broken: break

    stop_event.set()
    await monitor_task
    for nt in noise_tasks:
        nt.cancel()
    await asyncio.gather(*noise_tasks, return_exceptions=True)
    save_audit_dashboard(results, len(results), logger.cpu_usage, logger.mem_usage)
    logger.close()

if __name__ == "__main__":
    asyncio.run(run_mirror_test(50))