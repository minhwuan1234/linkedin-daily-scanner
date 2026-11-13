import os
import unittest
from unittest.mock import patch, MagicMock
from app.telemetry import LinkedInOutreachTelemetry

class TestLinkedInTelemetry(unittest.TestCase):
    def setUp(self):
        os.environ["FLEARNING_TELEMETRY_DISABLED"] = "false"

    def test_record_stage(self):
        tracker = LinkedInOutreachTelemetry(run_id="test_run_1", workload="10 profiles")
        tracker.record_stage("connect_send", "Gửi lời mời connect", 1540, "SUCCESS", "Send Connect Invitation")
        
        self.assertEqual(len(tracker.stages), 1)
        self.assertEqual(tracker.stages[0]["code"], "connect_send")
        self.assertEqual(tracker.stages[0]["nameEn"], "Send Connect Invitation")
        self.assertEqual(tracker.stages[0]["durationMs"], 1540)
        self.assertEqual(tracker.stages[0]["status"], "SUCCESS")

    @patch("urllib.request.urlopen")
    def test_finish_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        tracker = LinkedInOutreachTelemetry(run_id="test_run_2", workload="5 profiles")
        tracker.record_stage("connect_send", "Gửi lời mời connect", 2000, "SUCCESS")
        
        ok = tracker.finish("SUCCESS")
        self.assertTrue(ok)
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_zero_crash_on_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused / Timeout")

        tracker = LinkedInOutreachTelemetry(run_id="test_run_3")
        tracker.record_stage("connect_send", "Gửi lời mời connect", 1000, "SUCCESS")
        
        # Must not raise exception
        ok = tracker.finish("SUCCESS")
        self.assertFalse(ok)

if __name__ == "__main__":
    unittest.main()
