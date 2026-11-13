import os
import time
import json
import uuid
import urllib.request
from typing import Optional, List, Dict, Any

DEFAULT_DASHBOARD_URL = "https://dashboard-tool-performance.up.railway.app"
TOOL_SLUG = "linkedin-bd-outreach"
JOB_NAME = "Connect batch"
TIMEOUT_SECONDS = 3

class LinkedInOutreachTelemetry:
    """
    Telemetry Tracker chuyên biệt cho LinkedIn Daily Scanner / BD Outreach (v2.1).
    Hỗ trợ Timing Breakdown (Browser active vs Safety delay) và Account Pool Health.
    Tuân thủ F.Learning Telemetry Payload Contract v2.0/v2.1 và nguyên tắc Zero-Crash.
    """

    def __init__(self, run_id: Optional[str] = None, workload: Optional[str] = None):
        self.run_id = run_id or f"turn_{uuid.uuid4().hex[:10]}"
        self.workload = workload or "1 account turn"
        self.t0 = time.monotonic()
        self.stages: List[Dict[str, Any]] = []

    def record_stage(
        self,
        code: str,
        name: str,
        duration_ms: int,
        status: str = "SUCCESS",
        name_en: Optional[str] = None,
    ):
        """Ghi nhận thời gian và trạng thái của 1 giai đoạn / sub-job."""
        self.stages.append({
            "code": code,
            "name": name,
            "nameEn": name_en,
            "durationMs": max(1, int(duration_ms)),
            "status": "SUCCESS" if str(status).upper() == "SUCCESS" else "ERROR",
        })

    def finish(
        self,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        click_latency_ms: Optional[int] = None,
        browser_active_ms: Optional[int] = None,
        safety_delay_ms: Optional[int] = None,
        account_pool_health: Optional[Dict[str, Any]] = None,
        funnel_snapshot: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Gửi payload telemetry về Dashboard ngầm qua POST HTTP.
        Fail-safe 100%: Nuốt lỗi nếu mạng timeout hoặc Dashboard bảo trì.
        """
        if os.getenv("FLEARNING_TELEMETRY_DISABLED") == "true":
            return False

        total_ms = duration_ms or max(1, int((time.monotonic() - self.t0) * 1000))
        base_url = os.getenv("FLEARNING_DASHBOARD_URL", DEFAULT_DASHBOARD_URL).rstrip("/")
        secret = os.getenv("FLEARNING_TELEMETRY_SECRET", "")

        # Tự động tính timing breakdown nếu chưa truyền vào
        b_ms = browser_active_ms if browser_active_ms is not None else int(total_ms * 0.22)
        s_ms = safety_delay_ms if safety_delay_ms is not None else max(0, total_ms - b_ms)

        payload: Dict[str, Any] = {
            "schemaVersion": "2.1",
            "runId": self.run_id,
            "toolSlug": TOOL_SLUG,
            "jobName": JOB_NAME,
            "status": "SUCCESS" if str(status).upper() == "SUCCESS" else "ERROR",
            "durationMs": total_ms,
            "responseTimeMs": response_time_ms or 150,
            "clickLatencyMs": click_latency_ms or 90,
            "workload": self.workload,
            "errorMessage": error_message,
            "timingBreakdown": {
                "browserExecutionMs": b_ms,
                "safetyDelayMs": s_ms,
            },
            "stages": self.stages,
        }

        if account_pool_health:
            payload["accountPoolHealth"] = account_pool_health

        if funnel_snapshot:
            payload["funnelSnapshot"] = funnel_snapshot

        try:
            req = urllib.request.Request(
                f"{base_url}/api/webhooks/telemetry/{TOOL_SLUG}",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    **({"Authorization": f"Bearer {secret}"} if secret else {}),
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                return resp.status == 200
        except Exception:
            # Nguyên tắc Zero-Crash: Không bao giờ làm ảnh hưởng đến worker chính
            return False
