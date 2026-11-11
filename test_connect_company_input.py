import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from app.outreach_connect_input import prepare_connect_entries

try:
    from app import outreach_job_store as store
except ModuleNotFoundError as exc:
    if exc.name not in {"supabase", "dotenv"}:
        raise
    supabase = ModuleType("supabase")
    supabase.Client = object
    supabase.create_client = lambda *args, **kwargs: None
    settings = ModuleType("app.settings")
    settings.load_settings = lambda: None
    with patch.dict(sys.modules, {"supabase": supabase, "app.settings": settings}):
        from app import outreach_job_store as store


class ConnectCompanyInputTest(unittest.TestCase):
    def test_blank_urls_are_not_removed_when_pairing(self):
        with self.assertRaisesRegex(ValueError, "Row 2"):
            prepare_connect_entries(["url-a", "", "url-c"], ["A", "B", "C"])

    def test_mismatch_and_missing_names_are_rejected(self):
        for names in (["A"], ["A", ""], "A\nB", ["A", 2]):
            with self.subTest(names=names), self.assertRaises(ValueError):
                prepare_connect_entries(["url-a", "url-b"], names)

    def test_optional_companies_keep_existing_url_input(self):
        self.assertEqual(prepare_connect_entries([" url-a ", "", "url-b"]),
                         [("url-a", ""), ("url-b", "")])

    def _client(self, existing=()):
        client = MagicMock()
        tables = {name: MagicMock() for name in (store.JOB_TABLE, store.PROSPECT_TABLE, store.TARGET_TABLE)}
        client.table.side_effect = tables.__getitem__
        tables[store.JOB_TABLE].insert.return_value.execute.return_value = SimpleNamespace(data=[{"id": "job-1"}])
        lookup = tables[store.PROSPECT_TABLE].select.return_value.in_
        lookup.side_effect = lambda column, urls: MagicMock(**{"execute.return_value": SimpleNamespace(
            data=[{"normalized_url": url} for url in urls if url in existing])})

        def insert_prospects(rows):
            # Supabase may return rows in any order; ids are matched by normalized_url.
            data = [{"id": "p-" + row["normalized_url"].rsplit("/", 1)[-1], "normalized_url": row["normalized_url"]}
                    for row in reversed(rows)]
            return MagicMock(**{"execute.return_value": SimpleNamespace(data=data)})

        tables[store.PROSPECT_TABLE].insert.side_effect = insert_prospects
        return client, tables

    def test_skipped_urls_do_not_shift_companies(self):
        client, tables = self._client(existing={"https://www.linkedin.com/in/old"})
        urls = ["invalid", "https://linkedin.com/in/a", "https://www.linkedin.com/in/a/", "https://linkedin.com/in/old", "https://linkedin.com/in/b"]
        names = ["Invalid Co", "Company A", "Duplicate Co", "Existing Co", "Company B"]
        with patch.object(store, "_build_job_code", return_value="code"):
            result = store.create_connect_job(urls, company_names=names, client=client)
        rows = tables[store.PROSPECT_TABLE].insert.call_args.args[0]
        self.assertEqual([row["company_name"] for row in rows], ["Company A", "Company B"])
        self.assertEqual([row["normalized_url"] for row in rows], ["https://www.linkedin.com/in/a", "https://www.linkedin.com/in/b"])
        targets = tables[store.TARGET_TABLE].insert.call_args.args[0]
        self.assertEqual([t["prospect_id"] for t in targets], ["p-a", "p-b"])
        self.assertTrue(all(t["job_id"] == "job-1" and t["status"] == "pending" for t in targets))
        self.assertEqual((result.target_count, result.duplicate_count, result.invalid_count), (2, 2, 1))

    def test_large_batch_uses_a_few_calls_and_queues_the_job_last(self):
        client, tables = self._client()
        urls = [f"https://linkedin.com/in/p{i}" for i in range(150)]
        with patch.object(store, "_build_job_code", return_value="code"):
            result = store.create_connect_job(urls, client=client)
        self.assertEqual(result.target_count, 150)
        self.assertEqual(tables[store.PROSPECT_TABLE].select.return_value.in_.call_count, 3)
        self.assertEqual(tables[store.PROSPECT_TABLE].insert.call_count, 1)
        self.assertEqual(tables[store.TARGET_TABLE].insert.call_count, 1)
        self.assertEqual(tables[store.JOB_TABLE].insert.call_args.args[0]["status"], "creating")
        self.assertEqual(tables[store.JOB_TABLE].update.call_args.args[0]["status"], "pending")

    def test_all_duplicates_create_no_prospects(self):
        client, tables = self._client(existing={"https://www.linkedin.com/in/a"})
        with patch.object(store, "_build_job_code", return_value="code"):
            result = store.create_connect_job(["https://linkedin.com/in/a"], client=client)
        tables[store.PROSPECT_TABLE].insert.assert_not_called()
        tables[store.TARGET_TABLE].insert.assert_not_called()
        self.assertEqual((result.target_count, result.duplicate_count), (0, 1))

    def test_failed_targets_remove_new_prospects_and_keep_job_unqueued(self):
        client, tables = self._client()
        tables[store.TARGET_TABLE].insert.return_value.execute.side_effect = RuntimeError("network")
        with patch.object(store, "_build_job_code", return_value="code"), self.assertRaises(RuntimeError):
            store.create_connect_job(["https://linkedin.com/in/a", "https://linkedin.com/in/b"], client=client)
        tables[store.PROSPECT_TABLE].delete.return_value.in_.assert_called_once_with("id", ["p-a", "p-b"])
        tables[store.JOB_TABLE].update.assert_not_called()

    def test_bad_counts_fail_before_any_database_write(self):
        client = MagicMock()
        with self.assertRaises(store.OutreachJobStoreError):
            store.create_connect_job(["url-a", "url-b"], company_names=["A"], client=client)
        client.table.assert_not_called()

    def test_unavailable_column_fails_before_job_creation(self):
        client = MagicMock()
        client.table.return_value.select.return_value.limit.return_value.execute.side_effect = RuntimeError("column missing")
        with self.assertRaisesRegex(store.OutreachJobStoreError, "company-name storage"):
            store.create_connect_job(["https://linkedin.com/in/a"], company_names=["A"], client=client)
        client.table.return_value.insert.assert_not_called()


if __name__ == "__main__":
    unittest.main()
