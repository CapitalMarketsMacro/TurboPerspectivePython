import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.execution import FX_SCHEMA


class TestPerspectiveManager(unittest.TestCase):
    @patch("perspective_manager.perspective")
    def test_init_creates_table_with_schema(self, mock_perspective):
        mock_server = MagicMock()
        mock_client = MagicMock()
        mock_perspective.Server.return_value = mock_server
        mock_server.new_local_client.return_value = mock_client

        settings = MagicMock()
        settings.perspective_table_limit = 100_000

        from perspective_manager import PerspectiveManager

        pm = PerspectiveManager(settings)

        mock_client.table.assert_called_once_with(
            FX_SCHEMA,
            name="fx_executions",
            limit=100_000,
        )

    @patch("perspective_manager.perspective")
    def test_update_empty_list_does_not_call_table_update(self, mock_perspective):
        mock_server = MagicMock()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_perspective.Server.return_value = mock_server
        mock_server.new_local_client.return_value = mock_client
        mock_client.table.return_value = mock_table

        settings = MagicMock()
        settings.perspective_table_limit = 200_000

        from perspective_manager import PerspectiveManager

        pm = PerspectiveManager(settings)
        pm.update([])

        mock_table.update.assert_not_called()

    @patch("perspective_manager.perspective")
    def test_update_with_rows_calls_table_update(self, mock_perspective):
        mock_server = MagicMock()
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_perspective.Server.return_value = mock_server
        mock_server.new_local_client.return_value = mock_client
        mock_client.table.return_value = mock_table

        settings = MagicMock()
        settings.perspective_table_limit = 200_000

        from perspective_manager import PerspectiveManager

        pm = PerspectiveManager(settings)
        row = {"trade_id": "T-001", "ccy_pair": "EUR/USD"}
        pm.update([row])

        mock_table.update.assert_called_once_with([row])


if __name__ == "__main__":
    unittest.main()
