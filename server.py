import argparse
import logging
import signal
import sys

from tornado.ioloop import IOLoop

from config import load_settings
from perspective_manager import PerspectiveManager
from feed_adapter import FeedAdapter
from handlers.websocket_handler import make_app


def main():
    parser = argparse.ArgumentParser(description="FX Executions Blotter Server")
    parser.add_argument(
        "--source",
        choices=["solace", "nats"],
        default="solace",
        help="Message feed source: solace (default) or nats",
    )
    args = parser.parse_args()

    settings = load_settings(feed_source=args.source)

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    log = logging.getLogger(__name__)

    pm = PerspectiveManager(settings)

    loop = IOLoop.current()

    adapter = FeedAdapter(pm, loop, settings.feed_flush_interval_ms)

    # Start the appropriate receiver
    if settings.feed_source == "solace":
        from solace_receiver import start_receiver

        service, receiver = start_receiver(settings, adapter)
        source_display = settings.solace_host
        queue_display = settings.solace_queue
    else:
        from nats_receiver import start_nats_receiver

        nats_recv = start_nats_receiver(settings, adapter)
        source_display = settings.nats_url
        queue_display = settings.nats_subject

    app = make_app(pm)
    app.listen(settings.perspective_port)

    limit_display = settings.perspective_table_limit or 200_000
    log.info(
        "\n========================================="
        "\n  FX Executions Blotter Server"
        "\n  Port      : %s"
        "\n  Table     : fx_executions (limit: %s rows)"
        "\n  Source    : %s"
        "\n  Broker    : %s"
        "\n  Queue     : %s"
        "\n  Flush     : %sms batch window"
        "\n=========================================",
        settings.perspective_port,
        limit_display,
        settings.feed_source.upper(),
        source_display,
        queue_display,
        settings.feed_flush_interval_ms,
    )

    def shutdown(signum, frame):
        log.info("Received signal %s, shutting down...", signum)
        if settings.feed_source == "solace":
            try:
                receiver.terminate()
            except Exception:
                log.exception("Error stopping Solace receiver")
            try:
                service.disconnect()
            except Exception:
                log.exception("Error disconnecting Solace service")
        else:
            try:
                nats_recv.stop()
            except Exception:
                log.exception("Error stopping NATS receiver")
        loop.add_callback(loop.stop)
        log.info("Server shutdown complete")

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    loop.start()


if __name__ == "__main__":
    main()
