"""Browser UI timings for AI Agent Lab (Tốc độ phản hồi / Độ nhạy thao tác).

The dashboard measures one action, "Start Connect", and posts two samples:
  clickLatency  click → the button shows "Creating job..." (second animation frame)
  responseTime  click → the new Connect batch is shown on the dashboard

Only the metric name, the duration and the time are stored: in Supabase table
outreach_ui_samples (outreach_ui_samples.sql) so samples survive redeploys, and in memory as a
fallback while the table does not exist.
"""

from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

TABLE = "outreach_ui_samples"
METRICS = {"clickLatency": 60_000, "responseTime": 600_000}  # metric → max milliseconds
MAX_BODY = 200
PER_HOUR = 60
MEMORY = 5000
READ_LIMIT = 5000

KPI_DESCRIPTIONS = {
    "responseTime": "Bấm 'Start Connect' → Connect batch mới hiển thị trên dashboard (đo trong trình duyệt)",
    "clickLatency": "Bấm 'Start Connect' → nút chuyển sang 'Creating job...' (đo trong trình duyệt)",
}


class UiSamples:
    def __init__(self, client_factory: Callable[[], Any] | None = None, *,
                 now: Callable[[], float] = time.time, per_hour: int = PER_HOUR) -> None:
        self._client_factory = client_factory
        self._now = now
        self._per_hour = per_hour
        self._memory: deque = deque(maxlen=MEMORY)
        self._hits: dict = {}

    def _client(self):
        return self._client_factory() if self._client_factory else None

    def record(self, body: bytes | str, ip: str = "") -> int:
        """HTTP status: 204 stored, 400 invalid, 413 too large, 429 rate limited."""
        if len(body) > MAX_BODY:
            return 413
        try:
            data = json.loads(body)
            metric = data.get("metric")
            value = float(data.get("ms"))
        except (ValueError, TypeError, AttributeError):
            return 400
        if metric not in METRICS or not (0 <= value <= METRICS[metric]) or value != value:
            return 400

        t = self._now()
        key = str(ip or "")[:64]
        recent = [x for x in self._hits.get(key, []) if t - x < 3600]
        if len(recent) >= self._per_hour:
            return 429
        recent.append(t)
        self._hits[key] = recent
        if len(self._hits) > 5000:
            self._hits.clear()

        sample = {"metric": metric, "ms": round(value, 1),
                  "created_at": datetime.fromtimestamp(t, timezone.utc).isoformat()}
        self._memory.append(sample)
        try:
            client = self._client()
            if client is not None:
                client.table(TABLE).insert(sample).execute()
        except Exception:
            pass  # kept in memory; the table may not exist yet
        return 204

    def recent(self, days: int) -> list:
        """Samples of the last `days` days: Supabase when readable, else this process's memory."""
        since = datetime.fromtimestamp(self._now(), timezone.utc) - timedelta(days=days)
        try:
            client = self._client()
            if client is not None:
                rows = (client.table(TABLE).select("metric,ms,created_at").gte("created_at", since.isoformat())
                        .order("created_at", desc=True).limit(READ_LIMIT).execute().data or [])
                return list(rows)
        except Exception:
            pass
        return [s for s in self._memory if s["created_at"] >= since.isoformat()]


def p95(values: list) -> dict:
    """Nearest-rank P95 in milliseconds, with the sample count."""
    ordered = sorted(v for v in values if isinstance(v, (int, float)) and v >= 0)
    if not ordered:
        return {"p95Ms": None, "samples": 0}
    return {"p95Ms": round(ordered[max(0, -(-95 * len(ordered) // 100) - 1)], 1), "samples": len(ordered)}


def performance_kpis(samples: list) -> dict:
    def values(metric: str) -> list:
        out = []
        for s in samples:
            try:
                if s.get("metric") == metric:
                    out.append(float(s.get("ms")))
            except (TypeError, ValueError):
                continue
        return out

    return {"responseTime": p95(values("responseTime")), "clickLatency": p95(values("clickLatency"))}
