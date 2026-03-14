import asyncio
import logging
import threading

import nats

from config import Settings
from feed_adapter import FeedAdapter

log = logging.getLogger(__name__)


class NatsReceiver:
    """
    Connects to NATS and subscribes to a plain subject (core NATS, no JetStream).
    Forwards message payloads to the FeedAdapter.

    Runs its own asyncio event loop on a background thread (NATS Python client
    is asyncio-native, while Tornado uses its own IOLoop).
    """

    def __init__(self, settings: Settings, feed_adapter: FeedAdapter):
        self._settings = settings
        self._adapter = feed_adapter
        self._nc = None
        self._sub = None
        self._loop = None
        self._thread = None

    def start(self) -> None:
        """Start the NATS consumer on a background thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="nats-receiver"
        )
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_subscribe())
        self._loop.run_forever()

    async def _connect_and_subscribe(self) -> None:
        options = {"servers": self._settings.nats_url}

        if self._settings.nats_creds_file:
            options["user_credentials"] = self._settings.nats_creds_file

        async def disconnected_cb():
            log.warning("NATS disconnected")

        async def reconnected_cb():
            log.info("NATS reconnected")

        async def error_cb(e):
            log.error("NATS error: %s", e)

        options["disconnected_cb"] = disconnected_cb
        options["reconnected_cb"] = reconnected_cb
        options["error_cb"] = error_cb

        self._nc = await nats.connect(**options)

        log.info(
            "Connected to NATS at %s, subscribing to subject '%s'",
            self._settings.nats_url,
            self._settings.nats_subject,
        )

        self._sub = await self._nc.subscribe(
            self._settings.nats_subject,
            cb=self._on_message,
        )

        log.info("NATS subscription active on '%s'", self._settings.nats_subject)

    async def _on_message(self, msg) -> None:
        """Called on the NATS asyncio thread for each message."""
        try:
            payload = msg.data.decode("utf-8")
            self._adapter.on_message(payload)
        except Exception as e:
            log.warning("Failed to process NATS message: %s", e)

    def stop(self) -> None:
        """Gracefully stop the NATS consumer."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)

    async def _shutdown(self) -> None:
        try:
            if self._sub:
                await self._sub.unsubscribe()
        except Exception:
            log.exception("Error unsubscribing from NATS")
        try:
            if self._nc and self._nc.is_connected:
                await self._nc.drain()
        except Exception:
            log.exception("Error draining NATS connection")
        self._loop.stop()


def start_nats_receiver(settings: Settings, feed_adapter: FeedAdapter) -> NatsReceiver:
    """Create and start a NATS core receiver. Returns the receiver for shutdown."""
    receiver = NatsReceiver(settings, feed_adapter)
    receiver.start()
    return receiver
