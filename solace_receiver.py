import logging

from solace.messaging.messaging_service import MessagingService
from solace.messaging.receiver.message_receiver import MessageHandler
from solace.messaging.receiver.inbound_message import InboundMessage
from solace.messaging.resources.topic_subscription import TopicSubscription

from config import Settings
from feed_adapter import FeedAdapter

log = logging.getLogger(__name__)


class _ServiceInterruptionListener:
    def on_service_interrupted(self, event):
        log.warning("Solace service interrupted: %s", event)

    def on_service_restored(self, event):
        log.info("Solace service restored: %s", event)


class ExecutionMessageHandler(MessageHandler):
    def __init__(self, feed_adapter: FeedAdapter):
        self._adapter = feed_adapter

    def on_message(self, message: InboundMessage) -> None:
        payload = message.get_payload_as_string()
        self._adapter.on_message(payload)


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
    Connect to Solace and start consuming via direct topic subscription.
    Returns the (service, receiver) tuple for shutdown.
    """
    service = build_messaging_service(settings)
    service.add_reconnection_listener(_ServiceInterruptionListener())

    topic = TopicSubscription.of(settings.solace_topic)
    receiver = (
        service.create_direct_message_receiver_builder()
        .with_subscriptions([topic])
        .build()
    )
    receiver.start()
    log.info("Solace direct receiver started on topic '%s'", settings.solace_topic)

    handler = ExecutionMessageHandler(feed_adapter)
    receiver.receive_async(handler)

    return service, receiver
