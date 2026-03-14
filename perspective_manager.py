import logging

import perspective

from config import Settings
from models.execution import FX_SCHEMA

log = logging.getLogger(__name__)


class PerspectiveManager:
    def __init__(self, settings: Settings):
        self._server = perspective.Server()
        self._client = self._server.new_local_client()
        limit = settings.perspective_table_limit or None
        self._table = self._client.table(
            FX_SCHEMA,
            name="fx_executions",
            limit=limit if limit else 200_000,
        )
        log.info("Perspective table 'fx_executions' created (limit=%s)", limit or 200_000)

    def update(self, rows: list[dict]) -> None:
        """Must be called on the Tornado IOLoop thread."""
        if rows:
            try:
                self._table.update(rows)
            except Exception:
                log.exception("Failed to update Perspective table with %d rows", len(rows))

    def get_server(self) -> perspective.Server:
        return self._server
