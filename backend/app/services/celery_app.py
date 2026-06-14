from celery import Celery
import os
from kombu import Queue
import redis
import logging

logger = logging.getLogger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
try:
    r_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    r_client.ping()
except Exception as redis_err:
    logger.critical(f"Redis fallback connection down on {REDIS_URL}:{redis_err}")
    r_client = None

celery = Celery(
    "chronos_tasks",
    broker=REDIS_URL,
    backend = REDIS_URL
)

celery.conf.update(
    task_default_queue="default",
    task_queues=(
        Queue("chat_queue", routing_key="chat.#"),
        Queue("plan_queue", routing_key="plan.#"),
    ),
    task_routes = {
        "mission.process_chat": {"queue": "chat_queue"},
        "mission.process_plan": {"queue": "plan_queue"},
        "mission.execute_lifecycle": {"queue": "plan_queue"},
    },
    worker_prefetch_multiplier=1,
    task_track_started = True,
    task_serialization="json",
    result_persistent=True,

    result_expires = 3600
)

logger.info(f"--- Chronos Celery initiated on {REDIS_URL} ---")