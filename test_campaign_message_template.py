import unittest
from types import SimpleNamespace
from unittest.mock import patch

from test_message_preparation_sources import store


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.start = 0
        self.end = 0

    def select(self, *_args):
        return self

    def neq(self, *_args):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def range(self, start, end):
        self.start, self.end = start, end
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows[self.start:self.end + 1])


class CampaignMessageTemplateTest(unittest.TestCase):
    def test_loads_latest_template_from_same_campaign_only(self):
        batch = {"id": "current", "campaign_id": "video", "campaign_name": "Video", "status": "prepared"}
        rows = [
            {"id": "other", "campaign_id": "mkt", "message_template": "wrong", "status": "prepared", "updated_at": "2026-10-07T12:00:00Z"},
            {"id": "saved", "campaign_id": "video", "message_template": "saved video template", "status": "prepared", "updated_at": "2026-10-07T11:00:00Z"},
            {"id": "old", "campaign_id": "video", "message_template": "original", "status": "prepared", "updated_at": "2026-10-07T10:00:00Z"},
        ]
        client = SimpleNamespace(table=lambda _name: FakeQuery(rows))
        with patch.object(store, "get_prepared_message_batch", return_value=batch), patch.object(
            store, "_attach_source_connect_ids_to_batches", side_effect=lambda *, client, batches: batches
        ):
            result = store.get_campaign_message_template_for_batch("current", client=client)

        self.assertEqual(result["message_template"], "saved video template")
        self.assertEqual(result["campaign_id"], "video")
        self.assertTrue(result["can_save"])


if __name__ == "__main__":
    unittest.main()
