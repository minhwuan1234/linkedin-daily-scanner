"""Offline regressions: no LinkedIn browser, DB access or connection actions."""
import ast
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


def checker_module():
    tree = ast.parse(Path('app/linkedin_acceptance_checker.py').read_text())
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom)
        and node.module.startswith(('playwright', 'app.'))
    )]
    module = ModuleType('_offline_acceptance_checker')
    module.__dict__.update(LinkedInBrowserTimeoutError=type('BrowserTimeout', (Exception,), {}),
                           LinkedInSessionError=type('SessionError', (Exception,), {}),
                           PlaywrightTimeoutError=type('PlaywrightTimeout', (Exception,), {}))
    with patch.dict(sys.modules, {module.__name__: module}):
        exec(compile(tree, 'offline_checker', 'exec'), module.__dict__)
    return module


class AcceptanceMoreMenuTests(unittest.TestCase):
    def setUp(self):
        self.checker = checker_module()
        self.page = MagicMock()
        self.page.url = 'https://linkedin.com/in/alice'
        self.main = self.page.locator.return_value
        self.main.count.return_value = 1
        self.main.locator.return_value.count.return_value = 0
        self.texts = self.main.get_by_text.return_value
        self.texts.count.return_value = 1
        self.node = self.texts.nth.return_value
        self.button = self.node.locator.return_value.first
        self.node.locator.return_value.count.return_value = 1
        self.button.get_attribute.return_value = None
        self.button.evaluate.return_value = 'profile-more'
        self.checker._sleep = MagicMock()
        self.checker._is_visible_locator = MagicMock(return_value=True)
        self.checker._click_locator = MagicMock(return_value=True)
        self.checker._wait_for_visible_menu = MagicMock(return_value=True)
        self.deadline = self.checker._build_deadline()

    def open_more(self):
        return self.checker._open_acceptance_more_menu(self.page, deadline=self.deadline)

    def test_text_match_can_be_the_button_itself_or_a_nested_span(self):
        self.assertTrue(self.open_more())
        self.node.locator.assert_called_once_with(
            "xpath=ancestor-or-self::*[self::button or @role='button'][1]")
        self.checker._click_locator.assert_called_once_with(self.button, deadline=self.deadline, maximum_ms=500)

    def test_missing_aria_expanded_does_not_skip_visible_more(self):
        self.button.get_attribute.return_value = None
        self.assertTrue(self.open_more())
        self.checker._wait_for_visible_menu.assert_called_once()

    def test_missing_first_render_retries_instead_of_returning_early(self):
        self.texts.count.side_effect = [0, 1]
        self.assertTrue(self.open_more())
        self.assertEqual(self.main.get_by_text.call_count, 2)
        self.main.get_by_text.assert_called_with('More', exact=True)

    def test_more_button_with_accessible_label_but_no_visible_text(self):
        self.texts.count.return_value = 0
        candidates = self.main.locator.return_value
        candidates.count.side_effect = [1]
        candidates.nth.return_value = self.button
        self.assertTrue(self.open_more())
        self.main.locator.assert_called_with("button[aria-label='More']")
        self.checker._click_locator.assert_called_once_with(
            self.button, deadline=self.deadline, maximum_ms=500)

    def test_missing_main_retries(self):
        self.main.count.side_effect = [0, 1]
        self.assertTrue(self.open_more())

    def test_generic_non_button_text_is_not_clicked(self):
        self.node.locator.return_value.count.return_value = 0
        self.assertFalse(self.open_more())
        self.checker._click_locator.assert_not_called()

    def test_invisible_more_is_not_clicked(self):
        self.checker._is_visible_locator.return_value = False
        self.assertFalse(self.open_more())
        self.checker._click_locator.assert_not_called()

    def test_click_without_visible_menu_is_not_success(self):
        self.checker._wait_for_visible_menu.return_value = False
        self.assertFalse(self.open_more())

    def test_already_open_menu_is_not_toggled_closed(self):
        self.button.get_attribute.return_value = 'true'
        self.checker._visible_menu_exists = MagicMock(return_value=True)
        self.assertTrue(self.open_more())
        self.checker._click_locator.assert_not_called()

    def test_successful_more_check_only_reads_remove_connection(self):
        self.checker._is_profile_not_found = MagicMock(return_value=False)
        self.checker._has_pending_state = MagicMock(return_value=False)
        self.checker._open_acceptance_ellipsis_menu = MagicMock(return_value=False)
        self.checker._has_remove_connection_in_more_menu = MagicMock(return_value=True)
        browser = SimpleNamespace(open_linkedin_url=MagicMock(return_value=self.page))
        result = self.checker.check_profile_acceptance(browser=browser, linkedin_url=self.page.url)
        self.assertEqual(result.status, 'accepted')
        self.checker._click_locator.assert_called_once_with(self.button, deadline=unittest.mock.ANY, maximum_ms=500)
        self.page.get_by_text.assert_not_called()

    def test_no_menu_confirmation_falls_back_to_accepted_after_pending_absent(self):
        self.checker._is_profile_not_found = MagicMock(return_value=False)
        self.checker._has_pending_state = MagicMock(return_value=False)
        self.checker._open_acceptance_ellipsis_menu = MagicMock(return_value=False)
        self.checker._wait_for_visible_menu.return_value = False
        self.checker._has_remove_connection_in_more_menu = MagicMock()
        result = self.checker.check_profile_acceptance(
            browser=SimpleNamespace(open_linkedin_url=MagicMock(return_value=self.page)),
            linkedin_url=self.page.url)
        self.assertEqual(result.status, 'accepted')
        self.checker._has_remove_connection_in_more_menu.assert_not_called()

    def test_pending_does_not_fall_back_or_open_menu(self):
        self.checker._is_profile_not_found = MagicMock(return_value=False)
        self.checker._has_pending_state = MagicMock(return_value=True)
        self.checker._open_acceptance_ellipsis_menu = MagicMock()
        result = self.checker.check_profile_acceptance(
            browser=SimpleNamespace(open_linkedin_url=MagicMock(return_value=self.page)),
            linkedin_url=self.page.url)
        self.assertEqual(result.status, 'pending')
        self.checker._open_acceptance_ellipsis_menu.assert_not_called()

    def test_missing_profile_content_cannot_be_accepted(self):
        self.checker._is_profile_not_found = MagicMock(return_value=False)
        self.main.count.return_value = 0
        result = self.checker.check_profile_acceptance(
            browser=SimpleNamespace(open_linkedin_url=MagicMock(return_value=self.page)),
            linkedin_url=self.page.url)
        self.assertEqual(result.status, 'check_failed')

    def test_menu_timeout_falls_back_only_after_pending_was_checked(self):
        self.checker._is_profile_not_found = MagicMock(return_value=False)
        self.checker._has_pending_state = MagicMock(return_value=False)
        self.checker._open_acceptance_ellipsis_menu = MagicMock(
            side_effect=self.checker.LinkedInAcceptanceCheckTimeout('slow menu'))
        browser = SimpleNamespace(open_linkedin_url=MagicMock(return_value=self.page))
        result = self.checker.check_profile_acceptance(browser=browser, linkedin_url=self.page.url)
        self.assertEqual(result.status, 'accepted')

        self.checker._has_pending_state.side_effect = self.checker.LinkedInAcceptanceCheckTimeout('slow profile')
        result = self.checker.check_profile_acceptance(browser=browser, linkedin_url=self.page.url)
        self.assertEqual(result.status, 'check_failed')

    def test_opened_menu_without_removal_is_not_accepted_by_fallback(self):
        self.checker._is_profile_not_found = MagicMock(return_value=False)
        self.checker._has_pending_state = MagicMock(return_value=False)
        self.checker._open_acceptance_ellipsis_menu = MagicMock(return_value=True)
        self.checker._has_remove_connection_in_ellipsis_menu = MagicMock(return_value=False)
        self.checker._open_acceptance_more_menu = MagicMock(return_value=False)
        result = self.checker.check_profile_acceptance(
            browser=SimpleNamespace(open_linkedin_url=MagicMock(return_value=self.page)),
            linkedin_url=self.page.url)
        self.assertEqual(result.status, 'declined_or_unknown')

    def test_both_menu_paths_accept_only_exact_removal_labels(self):
        menus = MagicMock()
        menu = menus.nth.return_value
        items = menu.locator.return_value
        item = items.nth.return_value
        menus.count.return_value = 1
        items.count.return_value = 1
        self.page.locator.return_value = menus

        for path in (self.checker._has_remove_connection_in_ellipsis_menu,
                     self.checker._has_remove_connection_in_more_menu):
            for label in ('Remove connection', 'Remove connect', '  REMOVE   CONNECT  '):
                with self.subTest(path=path.__name__, label=label):
                    item.inner_text.return_value = label
                    self.assertTrue(path(self.page, deadline=self.deadline))
            for label in ('Remove connect request', 'Connect', 'Remove connection request'):
                with self.subTest(path=path.__name__, label=label):
                    item.inner_text.return_value = label
                    self.assertFalse(path(self.page, deadline=self.deadline))

    def test_unroled_action_sheet_still_confirms_remove_connect(self):
        menus = MagicMock()
        menus.count.return_value = 0
        self.page.locator.return_value = menus
        absent = MagicMock()
        absent.count.return_value = 0
        visible = MagicMock()
        visible.count.return_value = 1
        self.page.get_by_text.side_effect = [absent, visible, absent, visible]

        self.assertTrue(self.checker._has_remove_connection_in_ellipsis_menu(
            self.page, deadline=self.deadline))
        self.assertTrue(self.checker._has_remove_connection_in_more_menu(
            self.page, deadline=self.deadline))
        self.checker._click_locator.assert_not_called()

    def test_ellipsis_click_confirms_action_sheet_without_menu_role(self):
        candidate = MagicMock()
        candidate.count.return_value = 1
        button = candidate.nth.return_value
        button.inner_text.return_value = ''
        button.evaluate.return_value = 'profile-ellipsis'
        button.get_attribute.return_value = None
        menus = MagicMock()
        menus.count.return_value = 0
        self.page.locator.side_effect = lambda selector: (
            menus if selector == "[role='menu']" else candidate)
        absent = MagicMock()
        absent.count.return_value = 0
        visible = MagicMock()
        visible.count.return_value = 1
        self.page.get_by_text.side_effect = [absent, visible]

        self.assertTrue(self.checker._open_acceptance_ellipsis_menu(
            self.page, deadline=self.deadline))
        self.checker._click_locator.assert_called_once_with(
            button, deadline=self.deadline, maximum_ms=500)

    def test_profile_timeout_allows_navigation_and_menu_checks(self):
        self.assertEqual(self.checker.PROFILE_TIMEOUT_MS, 30_000)


if __name__ == '__main__':
    unittest.main()
