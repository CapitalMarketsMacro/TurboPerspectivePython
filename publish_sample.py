"""
Sample publisher — sends a random FX execution to a NATS subject every second.
Uses plain NATS core pub/sub (no JetStream).
Reads NATS connection details from the same .env used by the server.
"""

import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timezone, timedelta

import nats
from dotenv import load_dotenv

load_dotenv()

NATS_URL = os.environ["NATS_URL"]
NATS_CREDS_FILE = os.environ.get("NATS_CREDS_FILE", "")
NATS_SUBJECT = os.environ.get("NATS_SUBJECT", "fx.executions")

CCY_PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF", "USD/CAD", "NZD/USD", "EUR/GBP"]
SIDES = ["BUY", "SELL"]
VENUES = ["EBS", "Reuters", "CBOE", "Currenex", "Hotspot", "FXAll"]
DESKS = ["EMEA_SPOT", "APAC_SPOT", "AMER_SPOT", "EMEA_FWD", "APAC_FWD"]
STATUSES = ["FILLED", "FILLED", "FILLED", "PARTIAL", "CANCELLED"]
COUNTERPARTIES = ["JPMORGAN", "GOLDMAN", "CITI", "BARCLAYS", "HSBC", "DEUTSCHE", "UBS", "MORGAN_STANLEY"]
TRADERS = [f"TR{i:03d}" for i in range(1, 21)]

BASE_RATES = {
    "EUR/USD": 1.0820, "GBP/USD": 1.2650, "USD/JPY": 151.50,
    "AUD/USD": 0.6530, "USD/CHF": 0.8820, "USD/CAD": 1.3580,
    "NZD/USD": 0.6080, "EUR/GBP": 0.8550,
}

_seq = 0


def make_execution() -> dict:
    global _seq
    _seq += 1

    ccy = random.choice(CCY_PAIRS)
    spot = BASE_RATES[ccy] + random.uniform(-0.0050, 0.0050)
    rate = spot + random.uniform(-0.0003, 0.0003)
    notional = random.choice([100_000, 250_000, 500_000, 1_000_000, 2_000_000, 5_000_000])
    side = random.choice(SIDES)
    pnl = round((rate - spot) * notional * (1 if side == "BUY" else -1), 2)

    now = datetime.now(timezone.utc)
    value_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    return {
        "trade_id": f"T-{now:%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
        "ccy_pair": ccy,
        "side": side,
        "notional": float(notional),
        "rate": round(rate, 6),
        "venue": random.choice(VENUES),
        "trader_id": random.choice(TRADERS),
        "desk": random.choice(DESKS),
        "status": random.choice(STATUSES),
        "exec_time": now.isoformat(),
        "value_date": value_date,
        "counterparty": random.choice(COUNTERPARTIES),
        "pnl": pnl,
        "spot_rate": round(spot, 6),
        "sequence_num": _seq,
    }


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
            print(f"  seq={execution['sequence_num']:>6}  {execution['ccy_pair']}  "
                  f"{execution['side']:4}  {execution['notional']:>12,.0f}  "
                  f"@ {execution['rate']:.6f}")
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping publisher...")
    finally:
        await nc.drain()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
