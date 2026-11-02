import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from urllib.error import HTTPError

from traderlab.research_engine.supabase import ConnectionFailure, SupabaseStore


class SupabaseConnectionTests(unittest.TestCase):
    def setUp(self):
        self.store = SupabaseStore("https://example.supabase.co", "sb_secret_test_only")

    def test_key_not_in_repr_or_http_error(self):
        self.assertNotIn("sb_secret_test_only", repr(self.store))
        error = HTTPError("https://example.supabase.co", 401, "sb_secret_test_only", {}, None)
        with patch("traderlab.research_engine.supabase.urlopen", side_effect=error):
            with self.assertRaises(ConnectionFailure) as caught:
                self.store.check_schema()
        self.assertEqual(str(caught.exception), "Supabase candles: HTTP 401")
        self.assertIsNone(caught.exception.__cause__)

    def test_rejects_untrusted_url_and_public_key(self):
        for url in ("http://example.supabase.co", "https://example.supabase.co.evil.test",
                    "https://example.supabase.co/path", "https://user@example.supabase.co"):
            with self.assertRaises(ValueError):
                SupabaseStore(url, "sb_secret_test")
        with self.assertRaises(ValueError):
            SupabaseStore("https://example.supabase.co", "sb_publishable_test")

    def test_refuses_group_readable_secret_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config"
            path.write_text("SUPABASE_URL=https://example.supabase.co\nSUPABASE_SECRET_KEY=sb_secret_test\n")
            path.chmod(0o640)
            with self.assertRaises(ValueError):
                SupabaseStore.from_env_file(path)
            path.chmod(0o600)
            self.assertEqual(SupabaseStore.from_env_file(path).url, self.store.url)

    def test_accepts_read_only_systemd_credential_only_in_private_runtime_directory(self):
        config = "SUPABASE_URL=https://example.supabase.co\nSUPABASE_SECRET_KEY=sb_secret_test\n"
        path = Path("/run/credentials/tradergo-test.service/research.env")
        with patch.dict("os.environ", {"CREDENTIALS_DIRECTORY": str(path.parent)}), \
                patch.object(Path, "read_text", return_value=config), \
                patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=0o440)):
            self.assertEqual(SupabaseStore.from_env_file(path).url, self.store.url)
        with patch.dict("os.environ", {"CREDENTIALS_DIRECTORY": "/tmp"}), \
                patch.object(Path, "read_text", return_value=config), \
                patch.object(Path, "stat", return_value=SimpleNamespace(st_mode=0o440)):
            with self.assertRaises(ValueError):
                SupabaseStore.from_env_file(Path("/tmp/research.env"))

    def test_paginates_past_api_row_limit_and_excludes_open_candles(self):
        pages = [[{"open_time": "2024-01-01T00:00:00+00:00"}],
                 [{"open_time": "2024-01-01T04:00:00+00:00"}], []]
        responses = [io.BytesIO(json.dumps(p).encode()) for p in pages]
        with patch("traderlab.research_engine.supabase.urlopen", side_effect=responses) as get:
            rows = self.store.closed_candles(provider="binance", market="um", symbol="BTCUSDT",
                                             interval="4h", start="2024-01-01", end="2024-01-02")
        self.assertEqual(len(rows), 2)
        self.assertIn("closed=eq.true", get.call_args_list[0].args[0].full_url)
        self.assertIn("open_time=gt.", get.call_args_list[1].args[0].full_url)

    def test_rejects_unexpected_response(self):
        with patch("traderlab.research_engine.supabase.urlopen", return_value=io.BytesIO(b'{}')):
            with self.assertRaises(ConnectionFailure):
                self.store.check_schema()


if __name__ == "__main__":
    unittest.main()
