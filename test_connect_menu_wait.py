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
    def make_page(self, label, aria='', href=''):
        item = MagicMock()
        item.inner_text.return_value = label
        item.get_attribute.side_effect = lambda name: {'aria-label': aria, 'href': href}.get(name)
        candidates = MagicMock()
        candidates.count.return_value = 1
        candidates.nth.return_value = item
        page = MagicMock()
        page.locator.return_value = candidates
        return page, item

    def test_connect_button_without_menuitem_role_is_clicked(self):
        page, item = self.make_page('Connect')
        with patch.object(action, '_get_profile_vanity_name', return_value='alice'), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_locator', return_value=True) as click:
            self.assertTrue(action._click_connect_in_visible_profile_popup(page, deadline=100))
        self.assertIs(click.call_args.args[0], item)
        click.assert_called_once()

    def test_remove_connection_is_not_clicked(self):
        page, _ = self.make_page('Remove connection')
        with patch.object(action, '_get_profile_vanity_name', return_value='alice'), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_locator') as click:
            self.assertFalse(action._click_connect_in_visible_profile_popup(page, deadline=100))
        click.assert_not_called()

    def test_custom_invite_for_other_profile_is_not_clicked(self):
        page, _ = self.make_page('Connect', href='/preload/custom-invite/?vanityName=bob')
        with patch.object(action, '_get_profile_vanity_name', return_value='alice'), \
             patch.object(action, '_is_visible_locator', return_value=True), \
             patch.object(action, '_click_locator') as click:
            self.assertFalse(action._click_connect_in_visible_profile_popup(page, deadline=100))
        click.assert_not_called()
