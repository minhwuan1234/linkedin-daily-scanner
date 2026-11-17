import os
import time
import json
import uuid
import threading
import urllib.request
from typing import Optional, List, Dict, Any

DEFAULT_DASHBOARD_URL = "https://dashboard-tool-performance.up.railway.app"
TOOL_SLUG = "linkedin-bd-outreach"
JOB_NAME = "Connect batch"
TIMEOUT_SECONDS = 3

STAGE_DESCRIPTIONS: Dict[str, str] = {
    "connect_send": "Playwright tự động mở trang hồ sơ LinkedIn và gửi lời mời kết nối (Connect).",
    "message_send": "Playwright tự động gửi tin nhắn theo chiến dịch tới các kết nối đã chấp nhận.",
    "profile_scan": "Playwright tự động quét thông tin hồ sơ và cập nhật trạng thái kết nối.",
}

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
        step_type: str = "NON_AI",
        description: Optional[str] = None,
        summary: Optional[str] = None,
    ):
        """Ghi nhận thời gian, phân loại AI/Non-AI và mô tả của 1 giai đoạn / sub-job."""
        resolved_description = description or STAGE_DESCRIPTIONS.get(code) or name
        self.stages.append({
            "code": code,
            "name": name,
            "nameEn": name_en,
            "description": resolved_description,
            "summary": summary or resolved_description,
            "stepType": "AI" if str(step_type).upper() == "AI" else "NON_AI",
            "durationMs": max(1, int(duration_ms)),
            "status": "SUCCESS" if str(status).upper() == "SUCCESS" else "ERROR",
        })

    def finish(
        self,
        status: str = "SUCCESS",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        browser_active_ms: Optional[int] = None,
        safety_delay_ms: Optional[int] = None,
        account_pool_health: Optional[Dict[str, Any]] = None,
        funnel_snapshot: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Gửi payload telemetry về Dashboard ngầm qua POST HTTP.
        Fail-safe 100%: Nuốt lỗi nếu mạng timeout hoặc Dashboard bảo trì.
        """
        if os.getenv("NODE_ENV") == "test" or os.getenv("FLEARNING_TELEMETRY_DISABLED") == "true":
            return False

        total_ms = duration_ms or max(1, int((time.monotonic() - self.t0) * 1000))
        base_url = os.getenv("FLEARNING_DASHBOARD_URL", DEFAULT_DASHBOARD_URL).rstrip("/")
        secret = os.getenv("FLEARNING_TELEMETRY_SECRET", "")

        business_metrics: Dict[str, Any] = {}
        if browser_active_ms is not None and safety_delay_ms is not None:
            business_metrics["timingBreakdown"] = {
                "browserExecutionMs": browser_active_ms,
                "safetyDelayMs": safety_delay_ms,
            }
        if account_pool_health:
            business_metrics["accountPoolHealth"] = account_pool_health
        if funnel_snapshot:
            business_metrics["funnelSnapshot"] = funnel_snapshot

        payload: Dict[str, Any] = {
            "schemaVersion": "2.2",
            "runId": self.run_id,
            "toolSlug": TOOL_SLUG,
            "jobName": JOB_NAME,
            "status": "SUCCESS" if str(status).upper() == "SUCCESS" else "ERROR",
            "durationMs": total_ms,
            "workload": self.workload,
            "errorMessage": error_message,
            "stages": self.stages,
        }
        if business_metrics:
            payload["businessMetrics"] = business_metrics

        def _dispatch() -> bool:
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
                return False

        # Test/sync mode if requested, otherwise non-blocking daemon thread
        if os.getenv("FLEARNING_TELEMETRY_SYNC") == "true":
            return _dispatch()

        thread = threading.Thread(target=_dispatch, daemon=True)
        thread.start()
        return True
