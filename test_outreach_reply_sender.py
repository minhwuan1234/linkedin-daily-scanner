from __future__ import annotations

import unittest

from app.outreach_reply_direction import (
    classify_message_direction,
    incoming_after_last_own,
    merge_conversation_snapshots,
    profile_slug_key,
    sent_target_from_own_messages,
)


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

    def test_known_sent_text_does_not_override_customer_author(self) -> None:
        self.assertEqual(self.classify(
            author="Charlie Parkinson",
            text_value="Our outreach message",
            sent_message_text="Our outreach message",
        ), "incoming")

    def test_conflicting_dom_direction_is_unknown(self) -> None:
        self.assertEqual(self.classify(
            class_evidence="msg-s-event-listitem--is-me msg-s-event-listitem--incoming",
        ), "unknown")

    def test_explicit_incoming_dom_overrides_misleading_author(self) -> None:
        self.assertEqual(self.classify(
            class_evidence="msg-s-event-listitem--incoming",
            author="Linh Giang",
        ), "incoming")

    def test_relative_profile_link_matches_stored_url(self) -> None:
        self.assertEqual(
            profile_slug_key("/in/josh-lynch/?trk=messaging"),
            profile_slug_key("https://www.linkedin.com/in/josh-lynch/"),
        )

    def test_other_host_is_not_a_profile_match(self) -> None:
        self.assertEqual(profile_slug_key("https://example.com/in/josh-lynch"), "")

    def test_linkedin_country_subdomain_matches(self) -> None:
        self.assertEqual(
            profile_slug_key("https://uk.linkedin.com/in/josh-lynch"),
            profile_slug_key("https://linkedin.com/in/josh-lynch"),
        )

    def test_unique_own_sent_message_identifies_target(self) -> None:
        message = "Hey Josh, great to connect about the project."
        profiles = [
            {"id": "josh", "linkedin_url": "https://linkedin.com/in/josh-lynch", "message_text": message},
            {"id": "other", "linkedin_url": "https://linkedin.com/in/another-person", "message_text": "Hello another person, glad to connect."},
        ]
        events = [{"text": message, "is_own_message": True}]
        self.assertEqual(sent_target_from_own_messages(events, profiles)["id"], "josh")

    def test_incoming_quote_cannot_identify_target(self) -> None:
        message = "Hey Josh, great to connect about the project."
        profiles = [{"id": "josh", "linkedin_url": "https://linkedin.com/in/josh-lynch", "message_text": message}]
        events = [{"text": message, "is_own_message": False}]
        self.assertIsNone(sent_target_from_own_messages(events, profiles))

    def test_shared_template_is_not_unique_target(self) -> None:
        message = "Hello, lovely to connect with you."
        profiles = [
            {"id": "one", "linkedin_url": "https://linkedin.com/in/one", "message_text": message},
            {"id": "two", "linkedin_url": "https://linkedin.com/in/two", "message_text": message},
        ]
        events = [{"text": message, "is_own_message": True}]
        self.assertIsNone(sent_target_from_own_messages(events, profiles))

    def test_overlapping_history_windows_keep_repeated_real_messages(self) -> None:
        first = {"text": "Hello", "timestamp": "10:00", "sender_type": "own"}
        repeat = {"text": "Hello", "timestamp": "10:01", "sender_type": "own"}
        reply = {"text": "Hi", "timestamp": "10:02", "sender_type": "incoming"}
        self.assertEqual(
            merge_conversation_snapshots([first, repeat], [repeat, reply]),
            [first, repeat, reply],
        )

    def test_nonoverlapping_history_windows_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            merge_conversation_snapshots(
                [{"text": "old", "sender_type": "own"}],
                [{"text": "new", "sender_type": "incoming"}],
            )

    def test_incoming_never_confuses_own_message(self) -> None:
        events = [
            {"text": "from customer", "sender_type": "incoming"},
            {"text": "our answer", "sender_type": "own"},
            {"text": "new customer message", "sender_type": "incoming"},
        ]
        self.assertEqual(
            [event["text"] for event in incoming_after_last_own(events)],
            ["new customer message"],
        )


if __name__ == "__main__":
    unittest.main()
