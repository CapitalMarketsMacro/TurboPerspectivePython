import json
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is importable
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from feed_adapter import FeedAdapter

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_sample():
    with open(os.path.join(FIXTURES_DIR, "sample_execution.json")) as f:
        return f.read()


class TestFeedAdapterOnMessage(unittest.TestCase):
    def setUp(self):
        self.pm = MagicMock()
        self.loop = MagicMock()
        self.adapter = FeedAdapter(self.pm, self.loop, flush_interval_ms=50)

    def test_valid_json_enqueues_via_ioloop(self):
        payload = _load_sample()
        self.adapter.on_message(payload)
        self.loop.add_callback.assert_called_once()
        args = self.loop.add_callback.call_args
        self.assertEqual(args[0][0], self.adapter._enqueue)
        row = args[0][1]
        self.assertEqual(row["trade_id"], "T-20240314-001")

    def test_invalid_json_does_not_enqueue(self):
        with patch("feed_adapter.log") as mock_log:
            self.adapter.on_message("NOT VALID JSON {{{")
            self.loop.add_callback.assert_not_called()
            mock_log.warning.assert_called_once()

    def test_missing_trade_id_does_not_enqueue(self):
        payload = json.dumps({"ccy_pair": "EUR/USD"})
        with patch("feed_adapter.log") as mock_log:
            self.adapter.on_message(payload)
            self.loop.add_callback.assert_not_called()
            mock_log.warning.assert_called_once()


class TestFeedAdapterFlush(unittest.TestCase):
    def setUp(self):
        self.pm = MagicMock()
        self.loop = MagicMock()
        self.adapter = FeedAdapter(self.pm, self.loop, flush_interval_ms=50)

    def test_flush_calls_update_with_accumulated_rows(self):
        row1 = {"trade_id": "A", "ccy_pair": "EUR/USD"}
        row2 = {"trade_id": "B", "ccy_pair": "GBP/USD"}
        self.adapter._pending = [row1, row2]
        self.adapter._flush_scheduled = True

        self.adapter._flush()

        self.pm.update.assert_called_once_with([row1, row2])

    def test_flush_clears_pending_and_flag(self):
        self.adapter._pending = [{"trade_id": "A"}]
        self.adapter._flush_scheduled = True

        self.adapter._flush()

        self.assertEqual(self.adapter._pending, [])
        self.assertFalse(self.adapter._flush_scheduled)

    def test_flush_empty_does_not_call_update(self):
        self.adapter._pending = []
        self.adapter._flush_scheduled = True

        self.adapter._flush()

        self.pm.update.assert_not_called()
        self.assertFalse(self.adapter._flush_scheduled)


if __name__ == "__main__":
    unittest.main()
