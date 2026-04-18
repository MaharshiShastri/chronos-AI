import asyncio
import httpx
import time
import statistics
import os
import matplotlib.pyplot as plt
from tqdm import tqdm

BASE_URL = "http://localhost:8000"
MISSION_ID = 7
TIMESTAMP = int(time.time())
LOG_FILE = f"logs/benchmark_m{MISSION_ID}_{TIMESTAMP}.txt"
CHART_FILE = f"logs/visual_m{MISSION_ID}_{TIMESTAMP}.png"

os.makedirs("logs", exist_ok=True)

class FileLogger:
    def __init__(self, filepath):
        self.file = open(filepath, "a", encoding="utf-8")
    def log(self, message):
        print(message)
        self.file.write(message + "\n")
        self.file.flush()
    def close(self):
        self.file.close()

logger = FileLogger(LOG_FILE)

def save_visuals(results, user_count):
    """Generates a professional performance dashboard."""
    durations = [r['duration'] for r in results if r['success']]
    failures = user_count - len(durations)
    
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # 1. Latency Distribution (Histogram)
    ax1.hist(durations, bins=15, color='#00ffcc', edgecolor='black', alpha=0.7)
    ax1.set_title(f"Latency Distribution (P99: {max(durations if durations else [0])}s)")
    ax1.set_xlabel("Seconds")
    ax1.set_ylabel("Number of Users")
    ax1.grid(axis='y', linestyle='--', alpha=0.3)

    # 2. Success vs Failure (Pie Chart)
    ax2.pie([len(durations), failures], 
            labels=['Success', 'Fail'], 
            colors=['#00ffcc', '#ff3333'], 
            autopct='%1.1f%%', 
            startangle=140,
            explode=(0.1, 0) if failures > 0 else (0, 0))
    ax2.set_title("Reliability Overview")

    plt.suptitle(f"Mission Control Stress Test: {user_count} Concurrent Users", fontsize=16)
    plt.tight_layout()
    plt.savefig(CHART_FILE)
    print(f"🎨 Dashboard saved to: {CHART_FILE}")

async def simulate_user(user_id, pbar):
    url = f"{BASE_URL}/execute/{MISSION_ID}"
    start_time = time.time()
    event_count = 0
    
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    res = {"id": user_id, "success": False, "error": f"HTTP {response.status_code}"}
                else:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            event_count += 1
                            pbar.set_description(f"User {user_id} active...")
                            if "REQUIRE_APPROVAL" in line:
                                print(f"DEBUG: User {user_id} requesting approval...")
                                await client.patch(f"{BASE_URL}/approve/{MISSION_ID}/STP-BAE942")

                    duration = round(time.time() - start_time, 2)
                    res = {"id": user_id, "success": True, "duration": duration, "events": event_count}
            
            status = "✅ PASS" if res['success'] else "❌ FAIL"
            logger.log(f"{res['id']:<5} | {status:<10} | {res.get('duration', 0):>7}s | {res.get('events', 0):<8}")
            pbar.update(1)
            return res

        except Exception as e:
            logger.log(f"{user_id:<5} | ❌ FAIL     | N/A        | {str(e)[:20]}")
            pbar.update(1)
            return {"id": user_id, "success": False, "error": str(e)}

async def run_benchmarked_test(user_count):
    logger.log(f"🚀 MISSION {MISSION_ID} BENCHMARK: {user_count} USERS\n")
    logger.log(f"{'ID':<5} | {'STATUS':<10} | {'LATENCY':<10} | {'EVENTS':<8}\n" + "-"*50)
    
    with tqdm(total=user_count, desc="Benchmarking", leave=False) as pbar:
        tasks = [simulate_user(i, pbar) for i in range(user_count)]
        results = await asyncio.gather(*tasks)

    # Final stats & Visuals
    save_visuals(results, user_count)
    logger.close()

if __name__ == "__main__":
  user_count = int(input("Enter the number of concurrent users:"))
    asyncio.run(run_benchmarked_test(user_count))
