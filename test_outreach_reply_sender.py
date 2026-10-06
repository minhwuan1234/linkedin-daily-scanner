from __future__ import annotations

import unittest

from app.outreach_reply_direction import classify_message_direction


class ReplySenderTests(unittest.TestCase):
    def classify(self, **overrides: str) -> str:
        values = {
            "class_evidence": "",
            "author": "",
            "account_name": "Linh Giang",
            "unread_name": "Charlie Parkinson",
            "text_value": "Hello",
            "sent_message_text": "",
        }
        values.update(overrides)
        return classify_message_direction(**values)

    def test_outgoing_class_overrides_misleading_author(self) -> None:
        self.assertEqual(self.classify(
            class_evidence="msg-s-message-group msg-s-message-group--is-me",
            author="Charlie Parkinson",
        ), "own")

    def test_account_name_reversed_still_counts_as_own(self) -> None:
        self.assertEqual(self.classify(author="Giang Linh"), "own")

    def test_prospect_author_is_incoming(self) -> None:
        self.assertEqual(self.classify(author="Charlie Parkinson"), "incoming")

    def test_unknown_sender_is_not_a_verified_reply(self) -> None:
        self.assertEqual(self.classify(author="Another person"), "unknown")

    def test_known_sent_text_is_own_message(self) -> None:
        self.assertEqual(self.classify(
            author="Charlie Parkinson",
            text_value="Our outreach message",
            sent_message_text="Our outreach message",
        ), "own")


if __name__ == "__main__":
    unittest.main()
