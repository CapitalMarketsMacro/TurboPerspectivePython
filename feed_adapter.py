import logging

from tornado.ioloop import IOLoop

from models.execution import parse_execution
from perspective_manager import PerspectiveManager

log = logging.getLogger(__name__)


class FeedAdapter:
    def __init__(
        self,
        perspective_manager: PerspectiveManager,
        loop: IOLoop,
        flush_interval_ms: int,
    ):
        self._pending: list[dict] = []
        self._flush_scheduled = False
        self._pm = perspective_manager
        self._loop = loop
        self._interval = flush_interval_ms / 1000.0

    def on_message(self, raw_payload: str) -> None:
        """Called on Solace thread — must not touch Perspective directly."""
        try:
            row = parse_execution(raw_payload)
        except Exception as e:
            log.warning("Failed to parse execution: %s", e)
            return
        self._loop.add_callback(self._enqueue, row)

    def _enqueue(self, row: dict) -> None:
        """Runs on IOLoop thread."""
        self._pending.append(row)
        if not self._flush_scheduled:
            self._flush_scheduled = True
            self._loop.call_later(self._interval, self._flush)

    def _flush(self) -> None:
        """Runs on IOLoop thread."""
        if self._pending:
            self._pm.update(self._pending)
            self._pending = []
        self._flush_scheduled = False
