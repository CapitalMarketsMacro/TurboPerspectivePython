"""
Sample Solace publisher — sends a random FX execution every second.
Uses direct messaging to a topic (no queues).
Reads connection details from the same .env used by the server.
"""

import json
import os
import time

from solace.messaging.messaging_service import MessagingService
from solace.messaging.resources.topic import Topic
from dotenv import load_dotenv

from sample_data import make_execution

load_dotenv()

SOLACE_HOST = os.environ["SOLACE_HOST"]
SOLACE_VPN = os.environ["SOLACE_VPN"]
SOLACE_USERNAME = os.environ["SOLACE_USERNAME"]
SOLACE_PASSWORD = os.environ["SOLACE_PASSWORD"]
SOLACE_TOPIC = os.environ.get("SOLACE_TOPIC", "fx/executions/>").rstrip("/>").rstrip(">")
SOLACE_TRUST_STORE_PATH = os.environ.get("SOLACE_TRUST_STORE_PATH", "")


def build_service() -> MessagingService:
    props = {
        "solace.messaging.transport.host": SOLACE_HOST,
        "solace.messaging.service.vpn-name": SOLACE_VPN,
        "solace.messaging.authentication.basic.username": SOLACE_USERNAME,
        "solace.messaging.authentication.basic.password": SOLACE_PASSWORD,
    }

    if SOLACE_TRUST_STORE_PATH:
        props["solace.messaging.tls.trust-store-path"] = SOLACE_TRUST_STORE_PATH
    else:
        props["solace.messaging.tls.cert-validated"] = False
        props["solace.messaging.tls.cert-reject-expired"] = False
        props["solace.messaging.tls.cert-validate-servername"] = False

    return MessagingService.builder().from_properties(props).build().connect()


def main():
    service = build_service()
    publisher = service.create_direct_message_publisher_builder().build()
    publisher.start()

    topic = Topic.of(f"{SOLACE_TOPIC}/blotter")
    print(f"Connected to Solace at {SOLACE_HOST}")
    print(f"Publishing to '{topic.get_name()}' every 1s  (Ctrl+C to stop)")

    try:
        while True:
            execution = make_execution()
            payload = json.dumps(execution)
            publisher.publish(destination=topic, message=payload)
            print(f"  seq={execution['sequence_num']:>6}  {execution['ccy_pair']}  "
                  f"{execution['side']:4}  {execution['notional']:>12,.0f}  "
                  f"@ {execution['rate']:.6f}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping publisher...")
    finally:
        publisher.terminate()
        service.disconnect()
        print("Done.")


if __name__ == "__main__":
    main()
