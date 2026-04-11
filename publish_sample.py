"""
Sample NATS publisher — sends a random FX execution every second.
Uses plain NATS core pub/sub (no JetStream).
Reads connection details from the same .env used by the server.
"""

import asyncio
import json
import os

import nats
from dotenv import load_dotenv

from sample_data import make_execution

load_dotenv()

NATS_URL = os.environ["NATS_URL"]
NATS_CREDS_FILE = os.environ.get("NATS_CREDS_FILE", "")
NATS_SUBJECT = os.environ.get("NATS_SUBJECT", "fx.executions")


async def main():
    options = {"servers": NATS_URL}
    if NATS_CREDS_FILE:
        options["user_credentials"] = NATS_CREDS_FILE

    nc = await nats.connect(**options)
    print(f"Connected to NATS at {NATS_URL}")
    print(f"Publishing to '{NATS_SUBJECT}' every 1s  (Ctrl+C to stop)")

    try:
        while True:
            execution = make_execution()
            payload = json.dumps(execution).encode()
            await nc.publish(NATS_SUBJECT, payload)
            # print(f"  seq={execution['sequence_num']:>6}  {execution['ccy_pair']}  "
            #       f"{execution['side']:4}  {execution['notional']:>12,.0f}  "
            #       f"@ {execution['rate']:.6f}")
            await asyncio.sleep(0.0005)
    except KeyboardInterrupt:
        print("\nStopping publisher...")
    finally:
        await nc.drain()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
