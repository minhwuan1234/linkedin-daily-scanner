"""Offline tests for the AI Agent Lab monitoring report; no Supabase or browser."""
import json
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.lab_monitoring import (
    MAIN_JOB, STEP_ACCEPTANCE, STEP_CONNECT, STEP_MESSAGE, STEP_REPLY, STEPS,
    build_report, job_runs,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


class FakeQuery:
    def __init__(self, client, table):
        self.client, self.table, self.columns = client, table, "*"
        self.ids = None
        self.since = None
        self.window = None
        self.cap = None

    def select(self, columns="*"):
        self.columns = columns
        return self

    def order(self, *_, **__):
        return self

    def limit(self, n):
        self.cap = n
        return self

    def gte(self, _field, value):
        self.since = value
        return self

    def range(self, start, end):
        self.window = (start, end)
        return self

    def in_(self, _field, ids):
        self.ids = set(ids)
        return self

    def execute(self):
        self.client.calls.append((self.table, self.columns))
        missing = [c for c in self.columns.split(",") if c in self.client.missing.get(self.table, ())]
        if missing:
            raise RuntimeError("column outreach_job_targets.started_at does not exist")
        rows = self.client.tables.get(self.table, [])
        if isinstance(rows, Exception):
            raise rows
        if self.ids is not None:
            rows = [r for r in rows if r.get("id") in self.ids]
        if self.since:
            rows = [r for r in rows if (r.get("updated_at") or "") >= self.since[:19]]
        if self.window:
            rows = rows[self.window[0]:self.window[1] + 1]
        if self.cap:
            rows = rows[:self.cap]
        if self.columns != "*":
            keep = self.columns.split(",")
            rows = [{k: v for k, v in r.items() if k in keep} for r in rows]
        return SimpleNamespace(data=rows)


class FakeClient:
    def __init__(self, tables, missing=None):
        self.tables, self.missing, self.calls = tables, missing or {}, []

    def table(self, name):
        return FakeQuery(self, name)


def tables():
    return {
        "outreach_jobs": [
            {"id": "j1", "status": "completed", "batch_name": "Lần 3", "display_name": "Video L&D",
             "target_count": 30, "created_at": "2026-11-09T01:00:00Z", "started_at": "2026-11-09T02:00:00Z",
             "completed_at": "2026-11-09T05:00:00Z", "processed_count": 30, "success_count": 28},
            {"id": "j2", "status": "running", "batch_name": "Lần 4", "display_name": "Video L&D",
             "target_count": 10, "created_at": "2026-11-10T09:00:00Z", "started_at": "2026-11-10T10:00:00Z"},
            {"id": "j3", "status": "pending", "batch_name": "Chưa chạy", "target_count": 5,
             "created_at": "2026-11-10T11:00:00Z"},
            # Older than the 61-day horizon, but a recent reply belongs to it.
            {"id": "j-old", "status": "completed", "batch_name": "Lần 1", "display_name": "Onboarding",
             "target_count": 120, "created_at": "2026-08-01T01:00:00Z", "started_at": "2026-08-01T02:00:00Z",
             "completed_at": "2026-08-02T02:00:00Z"},
            {"id": "j-older", "status": "failed", "batch_name": "Lần 0", "created_at": "2026-07-01T01:00:00Z",
             "started_at": "2026-07-01T02:00:00Z", "completed_at": "2026-07-01T03:00:00Z"},
        ],
        "outreach_job_targets": [
            {"id": "t1", "job_id": "j1", "status": "completed", "started_at": "2026-11-09T02:00:00Z",
             "completed_at": "2026-11-09T02:03:00Z", "updated_at": "2026-11-09T02:03:00Z",
             "linkedin_url": "https://linkedin.com/in/private-person", "full_name": "Private Person"},
            {"id": "t2", "job_id": "j1", "status": "failed", "started_at": None,
             "completed_at": "2026-11-09T02:10:00Z", "updated_at": "2026-11-09T02:10:00Z"},
            {"id": "t3", "job_id": "j2", "status": "pending", "updated_at": "2026-11-10T10:00:00Z"},
            {"id": "t-old", "job_id": "j-old", "status": "completed", "completed_at": "2026-08-01T03:00:00Z",
             "updated_at": "2026-08-01T03:00:00Z"},
        ],
        "outreach_acceptance_checks": [
            {"id": "a1", "source_job_id": "j1", "status": "completed", "started_at": "2026-11-10T01:00:00Z",
             "completed_at": "2026-11-10T01:04:00Z", "updated_at": "2026-11-10T01:04:00Z",
             "created_at": "2026-11-10T01:00:00Z"},
            {"id": "a2", "source_job_id": "j1", "status": "queued", "updated_at": "2026-11-10T02:00:00Z",
             "created_at": "2026-11-10T02:00:00Z"},
        ],
        "outreach_message_targets": [
            {"id": "m1", "batch_id": "b1", "source_target_id": "t1", "status": "sent",
             "started_at": "2026-11-10T03:00:00Z", "completed_at": "2026-11-10T03:00:40Z",
             "updated_at": "2026-11-10T03:00:40Z", "message_text": "Hi Private Person"},
            {"id": "m2", "batch_id": "b1", "source_target_id": "t1", "status": "processing",
             "started_at": "2026-11-10T11:59:00Z", "updated_at": "2026-11-10T11:59:00Z"},
            {"id": "m-old", "batch_id": "b0", "source_target_id": "t-old", "status": "sent",
             "started_at": "2026-08-05T03:00:00Z", "completed_at": "2026-08-05T03:01:00Z",
             "updated_at": "2026-08-05T03:01:00Z"},
        ],
        "outreach_message_batches": [
            {"id": "b1", "status": "completed", "started_at": "2026-11-10T03:00:00Z",
             "completed_at": "2026-11-10T03:05:00Z", "sent_count": 1, "created_at": "2026-11-10T02:59:00Z",
             "message_template": "Hi {first_name}"},
        ],
        "outreach_reply_send_jobs": [
            {"id": "r1", "sent_target_id": "m-old", "status": "sent", "started_at": "2026-11-10T08:00:00Z",
             "sent_at": "2026-11-10T08:00:30Z", "updated_at": "2026-11-10T08:00:30Z",
             "created_at": "2026-11-10T07:59:00Z", "user_name": "Private Person", "message_text": "Thanks!"},
        ],
        "outreach_account_sessions": [{"status": "logged_in", "created_at": "2026-11-01T00:00:00Z"}],
    }


def report(client=None):
    return build_report(client or FakeClient(tables()), 7, now=lambda: NOW)


class JobRunsTests(unittest.TestCase):
    def runs(self, client=None):
        return report(client)["jobRuns"]["runs"]

    def by_id(self, client=None):
        return {r["runId"]: r for r in self.runs(client)}

    def test_connect_batch_is_the_main_job_with_campaign_workload(self):
        runs = self.by_id()
        batch = runs["connect:j1"]
        self.assertEqual(batch["job"], MAIN_JOB)
        self.assertEqual(batch["status"], "success")
        self.assertEqual(batch["workload"], "Batch connect · Lần 3 - Video L&D (30 hồ sơ)")
        self.assertNotIn("parentRunId", batch)
        self.assertEqual(runs["connect:j2"]["status"], "running")
        self.assertIsNone(runs["connect:j2"]["endedAt"])
        self.assertNotIn("connect:j3", runs)

    def test_every_step_links_back_to_its_connect_batch(self):
        runs = self.by_id()
        expected = {
            "connect-target:t1": (STEP_CONNECT, "connect:j1", "success"),
            "connect-target:t2": (STEP_CONNECT, "connect:j1", "failed"),
            "acceptance:a1": (STEP_ACCEPTANCE, "connect:j1", "success"),
            "message:m1": (STEP_MESSAGE, "connect:j1", "success"),
            "message:m2": (STEP_MESSAGE, "connect:j1", "running"),
            "reply:r1": (STEP_REPLY, "connect:j-old", "success"),
        }
        for run_id, (job, parent, status) in expected.items():
            with self.subTest(run_id):
                self.assertEqual((runs[run_id]["job"], runs[run_id]["parentRunId"], runs[run_id]["status"]), (job, parent, status))
                self.assertEqual(runs[run_id]["parent"], MAIN_JOB)
                self.assertEqual(runs[run_id]["workload"], "")
        self.assertNotIn("acceptance:a2", runs)
        self.assertIsNone(runs["connect-target:t2"]["startedAt"])
        self.assertEqual(runs["connect-target:t1"]["startedAt"], "2026-11-09T02:00:00+00:00")

    def test_old_batches_are_kept_only_when_a_recent_step_belongs_to_them(self):
        runs = self.by_id()
        self.assertIn("connect:j-old", runs)
        self.assertEqual(runs["connect:j-old"]["workload"], "Batch connect · Lần 1 - Onboarding (120 hồ sơ)")
        self.assertNotIn("connect:j-older", runs)
        self.assertNotIn("message:m-old", runs)
        self.assertNotIn("connect-target:t-old", runs)

    def test_runs_are_newest_first(self):
        moments = [r["endedAt"] or r["startedAt"] for r in self.runs()]
        self.assertEqual(moments, sorted(moments, reverse=True))

    def test_missing_started_at_column_falls_back_and_still_reports(self):
        client = FakeClient(tables(), missing={"outreach_job_targets": ("started_at",)})
        runs = self.by_id(client)
        self.assertIsNone(runs["connect-target:t1"]["startedAt"])
        self.assertEqual(runs["connect-target:t1"]["status"], "success")

    def test_batch_without_size_or_name_still_has_a_workload(self):
        from app.lab_monitoring import batch_workload
        self.assertEqual(batch_workload({"created_at": "2026-11-09T20:00:00Z"}), "Batch connect · 10/11/2026")

    def test_truncation_marks_runs_incomplete(self):
        result = job_runs({"targets": [{"id": str(i), "job_id": "j", "status": "completed",
                                        "completed_at": "2026-11-10T01:00:00Z"} for i in range(5)]},
                          NOW, set(), limit=3)
        self.assertEqual(len(result["runs"]), 3)
        self.assertFalse(result["complete"])


class ReportTests(unittest.TestCase):
    def test_protocol_and_declared_main_job(self):
        data = report()
        self.assertEqual(data["protocol"], "app-monitoring-v1")
        main = data["profile"]["mainJob"]
        self.assertEqual(main["job"], MAIN_JOB)
        self.assertEqual(main["steps"], list(STEPS))
        self.assertTrue(data["jobRuns"]["complete"])
        self.assertEqual(data["database"]["status"], "ready")

    def test_no_personal_data_or_message_text_leaves_the_app(self):
        text = json.dumps(report(), ensure_ascii=False)
        for secret in ("Private Person", "linkedin.com/in", "Thanks!", "Hi {first_name}"):
            self.assertNotIn(secret, text)

    def test_sub_job_tables_are_read_with_only_the_needed_columns(self):
        client = FakeClient(tables())
        report(client)
        for table, columns in client.calls:
            if table in ("outreach_job_targets", "outreach_message_targets", "outreach_reply_send_jobs"):
                self.assertNotEqual(columns, "*", table)
                for private in ("linkedin_url", "full_name", "user_name", "message_text"):
                    self.assertNotIn(private, columns)

    def test_unreadable_table_is_explained_not_zeroed(self):
        data = tables()
        data["outreach_message_targets"] = RuntimeError("permission denied for table outreach_message_targets")
        result = report(FakeClient(data))
        diagnostics = result["profile"]["sections"][0]
        self.assertEqual(diagnostics["id"], "diagnostics")
        self.assertIn("outreach_message_targets", [row[0] for row in diagnostics["table"]["rows"]])
        self.assertIn("connect:j1", {r["runId"] for r in result["jobRuns"]["runs"]})

    def test_without_client_reports_the_reason(self):
        result = build_report(None, 7, now=lambda: NOW, client_error="Missing OUTREACH_SUPABASE_URL.")
        self.assertEqual(result["database"]["error"], "Missing OUTREACH_SUPABASE_URL.")
        self.assertEqual(result["jobRuns"]["runs"], [])

    def test_job_targets_env_accepts_known_jobs_only(self):
        with patch.dict(os.environ, {"LAB_JOB_TARGETS_MINUTES": json.dumps({MAIN_JOB: 180, "Other": 5, STEP_MESSAGE: -1})}):
            self.assertEqual(report()["profile"]["jobTargets"], {MAIN_JOB: 180})


class StartedAtTests(unittest.TestCase):
    def setUp(self):
        from app import outreach_result_store as store
        self.store = store
        store._started_at_retry_after = 0.0
        self.addCleanup(setattr, store, "_started_at_retry_after", 0.0)
        self.now = [1000.0]
        self.client = MagicMock()
        self.update = self.client.table.return_value.update

    def mark(self, target_id):
        self.store.mark_connect_target_started(self.client, target_id, clock=lambda: self.now[0])

    def test_saves_the_start_time(self):
        self.mark("t1")
        self.update.assert_called_once()
        self.assertIn("started_at", self.update.call_args.args[0])

    def test_missing_column_pauses_then_retries_without_restart(self):
        execute = self.update.return_value.eq.return_value.execute
        execute.side_effect = RuntimeError("column started_at does not exist")
        self.mark("t1")
        self.mark("t2")
        self.assertEqual(self.update.call_count, 1)
        # The SQL is applied meanwhile; after the pause the worker saves again.
        execute.side_effect = None
        self.now[0] += self.store.STARTED_AT_RETRY_SECONDS + 1
        self.mark("t3")
        self.mark("t4")
        self.assertEqual(self.update.call_count, 3)


class RouteTests(unittest.TestCase):
    def setUp(self):
        try:
            from fastapi.testclient import TestClient
            from backend import main
        except Exception as error:  # pragma: no cover - dependencies missing
            self.skipTest(f"backend not importable: {error}")
        self.main = main
        self.http = TestClient(main.app)

    def test_disabled_without_token_and_rejects_wrong_token(self):
        with patch.dict(os.environ, {"LAB_MONITORING_TOKEN": ""}):
            self.assertEqual(self.http.get("/internal/monitoring").status_code, 404)
        token = "x" * 40
        with patch.dict(os.environ, {"LAB_MONITORING_TOKEN": token}):
            self.assertEqual(self.http.get("/internal/monitoring", headers={"Authorization": "Bearer nope"}).status_code, 401)
            self.assertEqual(self.http.get("/internal/monitoring?days=31", headers={"Authorization": "Bearer " + token}).status_code, 422)
            with patch.object(self.main, "get_outreach_client", return_value=FakeClient(tables())), \
                    patch.object(self.main, "get_outreach_worker_activity", return_value={"tasks": []}):
                response = self.http.get("/internal/monitoring?days=7", headers={"Authorization": "Bearer " + token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(response.json()["profile"]["mainJob"]["job"], MAIN_JOB)

    def test_ui_sample_route_stores_valid_samples_only(self):
        with patch.object(self.main, "UI_SAMPLES", self.main.UiSamples(None)) as store:
            ok = self.http.post("/api/outreach/ui-samples", content='{"metric":"clickLatency","ms":48}')
            bad = self.http.post("/api/outreach/ui-samples", content='{"metric":"x","ms":1}')
            self.assertEqual((ok.status_code, bad.status_code), (204, 400))
            self.assertEqual([s["ms"] for s in store.recent(7)], [48.0])


if __name__ == "__main__":
    unittest.main()


class UiSampleTests(unittest.TestCase):
    def setUp(self):
        from app.outreach_ui_samples import UiSamples
        self.t = [1_794_000_000.0]
        self.UiSamples = UiSamples

    def store(self, client=None, **kw):
        return self.UiSamples((lambda: client) if client is not None else None, now=lambda: self.t[0], **kw)

    def test_validates_metric_value_and_size(self):
        s = self.store()
        self.assertEqual(s.record('{"metric":"clickLatency","ms":42.26}', "1.1.1.1"), 204)
        self.assertEqual(s.record('{"metric":"responseTime","ms":1500}', "1.1.1.1"), 204)
        for body in ('{"metric":"other","ms":1}', '{"metric":"clickLatency","ms":-1}',
                     '{"metric":"clickLatency","ms":60001}', '{"metric":"clickLatency"}', "nope", "[]",
                     '{"metric":"clickLatency","ms":NaN}'):
            with self.subTest(body):
                self.assertEqual(s.record(body, "1.1.1.1"), 400)
        self.assertEqual(s.record("x" * 201, "1.1.1.1"), 413)
        self.assertEqual([x["ms"] for x in s.recent(7)], [42.3, 1500.0])

    def test_rate_limits_per_ip_per_hour(self):
        s = self.store(per_hour=2)
        body = '{"metric":"clickLatency","ms":10}'
        self.assertEqual([s.record(body, "a"), s.record(body, "a"), s.record(body, "a"), s.record(body, "b")], [204, 204, 429, 204])
        self.t[0] += 3601
        self.assertEqual(s.record(body, "a"), 204)

    def test_saves_to_supabase_and_reads_it_back(self):
        client = MagicMock()
        rows = [{"metric": "responseTime", "ms": 900, "created_at": "2026-11-10T01:00:00+00:00"}]
        client.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(data=rows)
        s = self.store(client)
        s.record('{"metric":"responseTime","ms":900}', "a")
        inserted = client.table.return_value.insert.call_args.args[0]
        self.assertEqual(set(inserted), {"metric", "ms", "created_at"})
        self.assertEqual(s.recent(7), rows)

    def test_falls_back_to_memory_when_the_table_is_missing(self):
        client = MagicMock()
        client.table.return_value.insert.return_value.execute.side_effect = RuntimeError("relation does not exist")
        client.table.return_value.select.side_effect = RuntimeError("relation does not exist")
        s = self.store(client)
        self.assertEqual(s.record('{"metric":"clickLatency","ms":30}', "a"), 204)
        self.assertEqual([x["ms"] for x in s.recent(7)], [30.0])
        self.t[0] += 8 * 86400
        self.assertEqual(s.recent(7), [])

    def test_report_carries_p95_and_descriptions(self):
        from app.outreach_ui_samples import p95
        samples = [{"metric": "responseTime", "ms": v} for v in range(1, 21)] + [{"metric": "clickLatency", "ms": 35.5}]
        data = build_report(FakeClient(tables()), 7, now=lambda: NOW, ui_samples=samples)
        self.assertEqual(data["performanceKpis"]["responseTime"], {"p95Ms": 19, "samples": 20})
        self.assertEqual(data["performanceKpis"]["clickLatency"], {"p95Ms": 35.5, "samples": 1})
        self.assertIn("Start Connect", data["profile"]["kpiDescriptions"]["responseTime"])
        self.assertEqual(p95([]), {"p95Ms": None, "samples": 0})
        self.assertEqual(report()["performanceKpis"]["clickLatency"]["samples"], 0)


class DashboardTimingTests(unittest.TestCase):
    def test_start_connect_sends_both_timings(self):
        from pathlib import Path
        source = Path(__file__).with_name("frontend").joinpath("app.js").read_text(encoding="utf8")
        handler = source[source.index("async function createOutreachConnectJob"):]
        handler = handler[:handler.index("\nasync function ", 10)]
        self.assertIn('sendLabUiSample("clickLatency", labStartedAt)', handler)
        self.assertIn('sendLabUiSample("responseTime", labStartedAt)', handler)
        self.assertLess(handler.index("renderOutreachJob("), handler.index('sendLabUiSample("responseTime"'))
