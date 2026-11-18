"""Offline checks for Pending inside the profile action menu."""
import ast
import unittest
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock


def load_helper():
    tree = ast.parse(Path('app/linkedin_connect_action.py').read_text())
    names = {'_read_pending_in_open_profile_menu', '_pending_via_profile_ellipsis', '_pending_via_profile_more'}
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    module = ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')], level=0), *fns], type_ignores=[])
    env = {'_click_ellipsis_button': MagicMock(return_value=True),
           '_click_more_button': MagicMock(return_value=True),
           '_is_visible_locator': MagicMock(return_value=True),
           '_sleep': MagicMock(), 'time': time}
    exec(compile(ast.fix_missing_locations(module), '<pending-test>', 'exec'), env)
    return env


class PendingMenuTest(unittest.TestCase):
    def test_exact_pending_is_read_without_clicking_it(self):
        env = load_helper()
        page = MagicMock()
        scopes = page.locator.return_value
        scopes.count.return_value = 1
        items = scopes.nth.return_value.get_by_text.return_value
        items.count.return_value = 1
        self.assertTrue(env['_pending_via_profile_ellipsis'](page, deadline=time.monotonic() + 0.01))
        scopes.nth.return_value.get_by_text.assert_called_with('Pending', exact=True)
        items.nth.return_value.click.assert_not_called()
        page.keyboard.press.assert_called_once_with('Escape')

    def test_more_menu_is_opened_and_pending_is_never_clicked(self):
        env = load_helper()
        page = MagicMock()
        scopes = page.locator.return_value
        scopes.count.return_value = 1
        items = scopes.nth.return_value.get_by_text.return_value
        items.count.return_value = 1
        deadline = time.monotonic() + 0.01
        self.assertTrue(env['_pending_via_profile_more'](page, deadline=deadline))
        env['_click_more_button'].assert_called_once_with(
            page, deadline=deadline, allow_unconfirmed_click=True)
        items.nth.return_value.click.assert_not_called()
        page.keyboard.press.assert_called_once_with('Escape')

    def test_missing_pending_does_not_confirm_invitation(self):
        env = load_helper()
        page = MagicMock()
        page.locator.return_value.count.return_value = 0
        self.assertFalse(env['_pending_via_profile_ellipsis'](page, deadline=time.monotonic() + 0.01))
        page.keyboard.press.assert_called_once_with('Escape')


if __name__ == '__main__':
    unittest.main()
