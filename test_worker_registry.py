from app.orchestration.worker_registry import (
    WorkerRegistration,
    WorkerRegistry,
)
from app.settings import load_settings


settings = load_settings()

registry = WorkerRegistry(
    settings=settings
)

youtube_worker = WorkerRegistration(
    worker_id="youtube-hermes-01",
    worker_name="YouTube Hermes Worker",
    worker_type="youtube",
    capabilities=(
        "youtube_scan",
    ),
    max_concurrent_jobs=1,
)

result = registry.register(
    worker=youtube_worker,
    status="starting",
    worker_version="0.1.0",
)

print(result)
