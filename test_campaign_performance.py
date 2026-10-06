import sys
import unittest
from types import ModuleType
from unittest.mock import patch


try:
    from app.outreach_campaign_performance_store import aggregate_campaign_performance
except ModuleNotFoundError as exc:
    if exc.name != "supabase":
        raise
    supabase = ModuleType("supabase")
    supabase.Client = object
    dashboard = ModuleType("app.outreach_dashboard_store")
    dashboard.get_outreach_client = lambda: None
    with patch.dict(sys.modules, {"supabase": supabase, "app.outreach_dashboard_store": dashboard}):
        from app.outreach_campaign_performance_store import aggregate_campaign_performance


class CampaignPerformanceTest(unittest.TestCase):
    def test_same_campaign_aggregates_batches_without_duplicate_replies(self):
        jobs = [
            {"id": "b1", "job_code": "B-01", "display_name": "Video Agency", "created_at": "2026-10-06T10:00:00Z"},
            {"id": "b2", "job_code": "B-02", "display_name": " video  agency ", "created_at": "2026-10-05T10:00:00Z"},
            {"id": "b3", "job_code": "B-03", "display_name": "Other", "created_at": "2026-10-04T10:00:00Z"},
        ]
        targets = [
            {"id": "t1", "job_id": "b1", "prospect_id": "p1"},
            {"id": "t2", "job_id": "b2", "prospect_id": "p2"},
            {"id": "t3", "job_id": "b3", "prospect_id": "p3"},
        ]
        sent = [
            {"id": "m1", "source_target_id": "t1"},
            {"id": "m2", "source_target_id": "t2"},
            {"id": "m3", "source_target_id": "t3"},
        ]
        replies = [
            {"sent_target_id": "m1"}, {"sent_target_id": "m1"},
            {"sent_target_id": "m3"},
        ]
        campaigns = aggregate_campaign_performance(jobs, targets, sent, replies)
        video = next(row for row in campaigns if row["campaign_name"] == "Video Agency")
        other = next(row for row in campaigns if row["campaign_name"] == "Other")
        self.assertEqual(video["batch_ids"], ["B-01", "B-02"])
        self.assertEqual((video["added"], video["messaged"], video["replies"]), (2, 2, 1))
        self.assertEqual(video["reply_rate"], 50.0)
        self.assertEqual((other["added"], other["messaged"], other["replies"]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
