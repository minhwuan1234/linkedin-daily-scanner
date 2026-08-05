from app.orchestration.worker_registry import (
    WorkerRegistry,
)
from app.settings import load_settings


settings = load_settings()

registry = WorkerRegistry(
    settings=settings
)

result = registry.heartbeat(
    worker_id="youtube-hermes-01",
    status="idle",
    current_job_id=None,
    current_load=0,
)

print(result)
