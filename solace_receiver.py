import logging

from solace.messaging.messaging_service import MessagingService
from solace.messaging.receiver.message_receiver import MessageHandler
from solace.messaging.receiver.inbound_message import InboundMessage
from solace.messaging.resources.queue import Queue
from solace.messaging.config.missing_resources_creation_configuration import (
    MissingResourcesCreationStrategy,
)

from config import Settings
from feed_adapter import FeedAdapter

log = logging.getLogger(__name__)


class _ServiceInterruptionListener:
    def on_service_interrupted(self, event):
        log.warning("Solace service interrupted: %s", event)

    def on_service_restored(self, event):
        log.info("Solace service restored: %s", event)


class ExecutionMessageHandler(MessageHandler):
    def __init__(self, feed_adapter: FeedAdapter, receiver):
        self._adapter = feed_adapter
        self._receiver = receiver

    def on_message(self, message: InboundMessage) -> None:
        payload = message.get_payload_as_string()
        self._adapter.on_message(payload)
        self._receiver.ack(message)


def build_messaging_service(settings: Settings) -> MessagingService:
    return (
        MessagingService.builder()
        .from_properties(
            {
                "solace.messaging.transport.host": settings.solace_host,
                "solace.messaging.service.vpn-name": settings.solace_vpn,
                "solace.messaging.authentication.basic.username": settings.solace_username,
                "solace.messaging.authentication.basic.password": settings.solace_password,
            }
        )
        .build()
        .connect()
    )


def start_receiver(settings: Settings, feed_adapter: FeedAdapter):
    """
    Connect to Solace and start consuming.
    Returns the (service, receiver) tuple for shutdown.
    """
    service = build_messaging_service(settings)
    service.add_reconnection_listener(_ServiceInterruptionListener())

    receiver = (
        service.create_persistent_message_receiver_builder()
        .with_missing_resources_creation_strategy(
            MissingResourcesCreationStrategy.CREATE_ON_START
        )
        .build(Queue.durable_exclusively_shared_queue(settings.solace_queue))
    )
    receiver.start()
    log.info("Solace receiver started on queue '%s'", settings.solace_queue)

    handler = ExecutionMessageHandler(feed_adapter, receiver)
    receiver.receive_async(handler)

    return service, receiver
