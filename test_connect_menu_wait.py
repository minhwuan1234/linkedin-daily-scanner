"""Check that a delayed overflow menu can still be used to connect."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app import linkedin_connect_action as action


class ConnectMenuWaitTests(unittest.TestCase):
    def test_delayed_connect_menu_item_is_clicked_once(self):
        clock = [0.0]
        item = MagicMock()
        item.inner_text.return_value = 'Connect'
        candidates = MagicMock()
        candidates.count.side_effect = lambda: 1 if clock[0] >= 2.0 else 0
        candidates.nth.return_value = item
        page = SimpleNamespace(locator=lambda selector: candidates)

        def advance(_page, *, deadline, milliseconds):
            clock[0] += milliseconds / 1000

        with patch.object(action.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(action, '_sleep', side_effect=advance), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_locator', return_value=True) as click:
            self.assertTrue(action._click_connect_in_ellipsis_menu(page, deadline=10))
        click.assert_called_once()
        self.assertIs(click.call_args.args[0], item)

    def test_menu_without_connect_is_not_clicked(self):
        clock = [0.0]
        item = MagicMock()
        item.inner_text.return_value = 'Message'
        candidates = MagicMock()
        candidates.count.return_value = 1
        candidates.nth.return_value = item
        page = SimpleNamespace(locator=lambda selector: candidates)
        def advance(_page, *, deadline, milliseconds):
            clock[0] += milliseconds / 1000
        with patch.object(action.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(action, '_sleep', side_effect=advance), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_connect_in_visible_profile_popup', return_value=False), \
             patch.object(action, '_click_locator') as click:
            self.assertFalse(action._click_connect_in_ellipsis_menu(page, deadline=10))
        click.assert_not_called()


if __name__ == '__main__':
    unittest.main()

class PendingAfterSendTests(unittest.TestCase):
    def test_rechecks_more_after_delayed_invite_modal_is_sent(self):
        clock = [0.0]
        page = MagicMock()
        def advance(_page, *, deadline, milliseconds):
            clock[0] += milliseconds / 1000
        with patch.object(action.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(action, '_sleep', side_effect=advance), \
             patch.object(action, '_has_pending_state', return_value=False), \
             patch.object(action, '_has_invite_modal', side_effect=[False, True]), \
             patch.object(action, '_click_send_without_note', return_value=True) as send, \
             patch.object(action, '_pending_via_profile_more', side_effect=[False, True]) as more, \
             patch.object(action, '_pending_via_profile_ellipsis', return_value=False) as dots:
            result = action._confirm_after_connect_click(page, deadline=30)
        self.assertEqual(result, 'invitation_sent')
        send.assert_called_once()
        self.assertEqual(more.call_count, 2)
        self.assertEqual(dots.call_count, 1)

class FlexibleConnectPopupTests(unittest.TestCase):
    def make_page(self, *, found=True, href=None):
        node = MagicMock()
        link = node.locator.return_value
        link.count.return_value = int(href is not None)
        link.first.get_attribute.return_value = href
        popup = MagicMock()
        texts = popup.get_by_text.return_value
        texts.count.return_value = int(found)
        texts.nth.return_value = node
        popup.get_by_role.return_value.count.return_value = 0
        page = MagicMock()
        page.locator.return_value.count.return_value = 1
        page.locator.return_value.nth.return_value = popup
        return page, node

    def test_connect_text_without_menuitem_role_is_clicked(self):
        page, item = self.make_page()
        with patch.object(action, '_get_profile_vanity_name', return_value='alice'), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_locator', return_value=True) as click:
            self.assertTrue(action._click_connect_in_visible_profile_popup(page, deadline=100))
        self.assertIs(click.call_args.args[0], item)
        click.assert_called_once()

    def test_missing_connect_is_not_clicked(self):
        page, _ = self.make_page(found=False)
        with patch.object(action, '_get_profile_vanity_name', return_value='alice'), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_locator') as click:
            self.assertFalse(action._click_connect_in_visible_profile_popup(page, deadline=100))
        click.assert_not_called()

    def test_custom_invite_for_other_profile_is_not_clicked(self):
        page, _ = self.make_page(href='/preload/custom-invite/?vanityName=bob')
        with patch.object(action, '_get_profile_vanity_name', return_value='alice'), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_locator') as click:
            self.assertFalse(action._click_connect_in_visible_profile_popup(page, deadline=100))
        click.assert_not_called()


class SendWithoutNoteTests(unittest.TestCase):
    def test_retries_send_until_click_succeeds_before_checking_pending(self):
        clock = [0.0]
        page = MagicMock()
        def advance(_page, *, deadline, milliseconds):
            clock[0] += milliseconds / 1000
        with patch.object(action.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(action, '_sleep', side_effect=advance), \
             patch.object(action, '_has_pending_state', side_effect=[False, False, True]), \
             patch.object(action, '_has_invite_modal', return_value=True), \
             patch.object(action, '_click_send_without_note', side_effect=[False, True]) as send, \
             patch.object(action, '_pending_via_profile_more', return_value=False) as more, \
             patch.object(action, '_pending_via_profile_ellipsis', return_value=False) as dots:
            self.assertEqual(action._confirm_after_connect_click(page, deadline=30), 'invitation_sent')
        self.assertEqual(send.call_count, 2)
        more.assert_called_once()
        dots.assert_called_once()

    def test_finds_visible_send_button_after_hidden_match(self):
        page = MagicMock()
        candidates = page.locator.return_value
        candidates.count.return_value = 2
        first, second = MagicMock(), MagicMock()
        candidates.nth.side_effect = [first, second]
        with patch.object(action, '_is_visible_locator', side_effect=[False, True]):
            self.assertTrue(action._has_invite_modal(page, deadline=30))


class DirectConnectPriorityTests(unittest.TestCase):
    def test_direct_connect_does_not_open_menu_before_action(self):
        page = MagicMock()
        page.url = 'https://www.linkedin.com/in/alice'
        browser = MagicMock()
        browser.open_linkedin_url.return_value = page
        with patch.object(action, '_is_profile_not_found', return_value=False), \
             patch.object(action, '_has_pending_state', return_value=False), \
             patch.object(action, '_has_first_degree_state', return_value=False), \
             patch.object(action, '_click_direct_connect', return_value=True) as direct, \
             patch.object(action, '_pending_via_profile_more') as more, \
             patch.object(action, '_pending_via_profile_ellipsis') as ellipsis, \
             patch.object(action, '_confirm_after_connect_click', return_value='invitation_sent'):
            result = action.connect_profile(browser=browser, linkedin_url=page.url)
        self.assertEqual(result.status, 'invitation_sent')
        direct.assert_called_once()
        more.assert_not_called()
        ellipsis.assert_not_called()


class PendingMenuPriorityTests(unittest.TestCase):
    def test_menu_is_checked_even_if_pending_visible_after_send(self):
        clock = [0.0]
        page = MagicMock()
        events = []
        def advance(_page, *, deadline, milliseconds):
            clock[0] += milliseconds / 1000
        def send(*args, **kwargs):
            events.append('send')
            return True
        def more(*args, **kwargs):
            events.append('more')
            return True
        with patch.object(action.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(action, '_sleep', side_effect=advance), \
             patch.object(action, '_has_invite_modal', return_value=True), \
             patch.object(action, '_click_send_without_note', side_effect=send), \
             patch.object(action, '_has_pending_state', return_value=True), \
             patch.object(action, '_pending_via_profile_more', side_effect=more), \
             patch.object(action, '_pending_via_profile_ellipsis') as ellipsis:
            self.assertEqual(action._confirm_after_connect_click(page, deadline=30), 'invitation_sent')
        self.assertEqual(events, ['send', 'more'])
        ellipsis.assert_not_called()
