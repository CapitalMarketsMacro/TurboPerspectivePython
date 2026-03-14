# FX Executions Blotter — Perspective Python Server

## Overview

Build a production-grade streaming server that:

1. Subscribes to a **Solace PubSub+** broker to receive FX execution messages
2. Ingests those messages into a **Perspective** in-memory columnar table
3. Serves **50 concurrent trader clients** via WebSocket using **Tornado**
4. Delivers live delta updates to every connected `<perspective-viewer>` in the browser

The server is **read-only** from the client perspective — traders can filter, sort and group
but cannot write data back. The Solace feed is the sole write path.

---

## Project Structure

```
fx-blotter-server/
├── README.md                   ← this file
├── requirements.txt            ← Python dependencies
├── .env.example                ← environment variable template
├── config.py                   ← centralised configuration (loaded from .env)
├── server.py                   ← main entry point
├── perspective_manager.py      ← Perspective Server + Table lifecycle
├── solace_receiver.py          ← Solace persistent message receiver
├── feed_adapter.py             ← message parsing + batch coalescer
├── handlers/
│   └── websocket_handler.py    ← PerspectiveTornadoHandler wiring
├── models/
│   └── execution.py            ← FX Execution dataclass + schema definition
└── tests/
    ├── test_feed_adapter.py
    ├── test_perspective_manager.py
    └── fixtures/
        └── sample_execution.json
```

---

## Requirements

### Python Dependencies (`requirements.txt`)

```
perspective-python==4.1.1
tornado==6.4
pyarrow==18.1.0
solace-pubsubplus==1.11.0
python-dotenv==1.0.0
```

### Environment

- Python 3.12 (64-bit)
- Windows (local dev) or Linux x86_64 (production / OpenShift)
- Solace PubSub+ broker accessible from the host

---

## Environment Variables (`.env.example`)

Create a `.env` file by copying `.env.example` and filling in values.
The application must **never** have credentials hard-coded in source.

```env
# Solace broker connection
SOLACE_HOST=tcps://your-broker-host:55443
SOLACE_VPN=your-vpn-name
SOLACE_USERNAME=fx-blotter-svc
SOLACE_PASSWORD=your-password

# Solace queue name — must be pre-provisioned on the broker
SOLACE_QUEUE=fx.executions.blotter

# Perspective server
PERSPECTIVE_PORT=8080

# Feed batching — how often (ms) to flush pending rows into the Perspective table
# Lower = lower latency, higher = fewer table.update() calls
FEED_FLUSH_INTERVAL_MS=50

# Max rows the Perspective table will hold before oldest rows are dropped
# 0 = unlimited (use for full day replay)
PERSPECTIVE_TABLE_LIMIT=200000

# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
```

---

## Data Model (`models/execution.py`)

Define an `FxExecution` dataclass and the Perspective table schema.

### Fields

| Field           | Python type | Perspective type | Description                              |
|-----------------|-------------|------------------|------------------------------------------|
| `trade_id`      | `str`       | `string`         | Unique execution identifier (UUID)       |
| `ccy_pair`      | `str`       | `string`         | Currency pair e.g. `EUR/USD`             |
| `side`          | `str`       | `string`         | `BUY` or `SELL`                          |
| `notional`      | `float`     | `float`          | Trade notional in base currency          |
| `rate`          | `float`     | `float`          | Executed rate (6 decimal places)         |
| `venue`         | `str`       | `string`         | Execution venue e.g. `EBS`, `Reuters`    |
| `trader_id`     | `str`       | `string`         | Trader identifier                        |
| `desk`          | `str`       | `string`         | Trading desk e.g. `EMEA_SPOT`            |
| `status`        | `str`       | `string`         | `FILLED`, `PARTIAL`, `CANCELLED`         |
| `exec_time`     | `str`       | `datetime`       | Execution timestamp ISO-8601 UTC         |
| `value_date`    | `str`       | `date`           | Value date `YYYY-MM-DD`                  |
| `counterparty`  | `str`       | `string`         | Counterparty name                        |
| `pnl`           | `float`     | `float`          | Estimated P&L in USD                     |
| `spot_rate`     | `float`     | `float`          | Spot reference rate                      |
| `sequence_num`  | `int`       | `integer`        | Monotonically increasing sequence number |

### Implementation notes

- Define `FX_SCHEMA` as a `dict[str, type | str]` matching Perspective's schema format
- Define `parse_execution(raw: bytes | str) -> dict` that converts an inbound Solace
  message payload (JSON string) into a plain dict with the above fields
- Handle missing / null fields gracefully — use sensible defaults rather than raising
- Validate that `exec_time` is a parseable ISO-8601 string; if not, default to current UTC
- `trade_id` must always be present — raise `ValueError` if absent

---

## Configuration (`config.py`)

Load all settings from environment variables using `python-dotenv`. Expose a single
`Settings` dataclass (or simple module-level constants) so the rest of the codebase
imports from one place.

```python
# Example shape — implement using python-dotenv + os.environ
@dataclass
class Settings:
    solace_host: str
    solace_vpn: str
    solace_username: str
    solace_password: str
    solace_queue: str
    perspective_port: int
    feed_flush_interval_ms: int
    perspective_table_limit: int
    log_level: str
```

Raise a clear `EnvironmentError` at startup if any required variable is missing.

---

## Perspective Manager (`perspective_manager.py`)

Owns the Perspective `Server`, `Client` and `Table` lifecycle.

### Responsibilities

- Create a `perspective.Server()` instance
- Create a local client via `server.new_local_client()`
- Create the `fx_executions` table using `FX_SCHEMA` with the configured row limit
- Expose `update(rows: list[dict])` — called by the feed adapter on every flush
- Expose `get_server()` — returns the `Server` instance for the Tornado handler

### Key implementation detail

`table.update()` must be called **on the Tornado IOLoop thread**, not from any other thread.
The feed adapter must use `IOLoop.current().add_callback(perspective_manager.update, rows)`
to cross the thread boundary safely.

### Example skeleton

```python
import perspective
from models.execution import FX_SCHEMA
from config import Settings

class PerspectiveManager:
    def __init__(self, settings: Settings):
        self._server = perspective.Server()
        self._client = self._server.new_local_client()
        limit = settings.perspective_table_limit or None  # 0 means unlimited
        self._table = self._client.table(
            FX_SCHEMA,
            name="fx_executions",
            limit=limit if limit else 200_000,
        )

    def update(self, rows: list[dict]) -> None:
        """Must be called on the Tornado IOLoop thread."""
        if rows:
            self._table.update(rows)

    def get_server(self) -> perspective.Server:
        return self._server
```

---

## Feed Adapter (`feed_adapter.py`)

Sits between the Solace receiver and the Perspective table.
Implements a **batch coalescer** to avoid calling `table.update()` on every single message.

### Responsibilities

- Hold a list of pending rows received from the Solace callback thread
- On each message: append the parsed row and schedule a flush if not already scheduled
- Flush: call `table.update(pending_rows)` via `IOLoop.add_callback` then clear the list
- The flush is scheduled using `IOLoop.call_later(flush_interval_seconds)`

### Threading contract

The Solace `on_message` callback fires on a **Solace internal thread** — NOT the Tornado
IOLoop. Use `IOLoop.add_callback()` for everything that touches Perspective or Tornado state.

### Pseudocode

```python
class FeedAdapter:
    def __init__(self, perspective_manager, loop, flush_interval_ms):
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
        # Hand off to IOLoop
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
```

---

## Solace Receiver (`solace_receiver.py`)

Connects to Solace and starts consuming persistent (guaranteed) messages from the queue.

### Use persistent messaging

Use `PersistentMessageReceiver` with `receive_async(handler)`. This delivers messages to
the handler's `on_message` at least once. Do NOT use direct messaging — FX executions
cannot be lost even if the server restarts briefly.

### Message acknowledgement

Acknowledge each message **after** `feed_adapter.on_message()` returns successfully.
If parsing fails, still acknowledge (the row is logged as a warning) — do not leave
unacknowledged messages piling up on the broker.

### Reconnection

The Solace Python API handles reconnection automatically. Register a
`ServiceInterruptionListener` to log disconnection / reconnection events. Do not attempt
manual reconnect logic.

### Implementation skeleton

```python
from solace.messaging.messaging_service import MessagingService
from solace.messaging.receiver.message_receiver import MessageHandler
from solace.messaging.receiver.inbound_message import InboundMessage
from solace.messaging.resources.queue import Queue
from solace.messaging.config.missing_resources_creation_configuration import (
    MissingResourcesCreationStrategy,
)

class ExecutionMessageHandler(MessageHandler):
    def __init__(self, feed_adapter, receiver):
        self._adapter = feed_adapter
        self._receiver = receiver

    def on_message(self, message: InboundMessage) -> None:
        payload = message.get_payload_as_string()
        self._adapter.on_message(payload)
        self._receiver.ack(message)


def build_messaging_service(settings) -> MessagingService:
    return (
        MessagingService.builder()
        .from_properties({
            "solace.messaging.transport.host": settings.solace_host,
            "solace.messaging.service.vpn-name": settings.solace_vpn,
            "solace.messaging.authentication.basic.username": settings.solace_username,
            "solace.messaging.authentication.basic.password": settings.solace_password,
        })
        .build()
        .connect()
    )


def start_receiver(settings, feed_adapter) -> None:
    """
    Connect to Solace and start consuming.
    Returns immediately — messages arrive asynchronously via the handler callback.
    """
    service = build_messaging_service(settings)
    receiver = (
        service.create_persistent_message_receiver_builder()
        .with_missing_resources_creation_strategy(
            MissingResourcesCreationStrategy.CREATE_ON_START
        )
        .build(Queue.durable_exclusively_shared_queue(settings.solace_queue))
    )
    receiver.start()
    handler = ExecutionMessageHandler(feed_adapter, receiver)
    receiver.receive_async(handler)
```

---

## WebSocket Handler (`handlers/websocket_handler.py`)

Wire the Perspective Tornado handler into the Tornado application.

```python
from concurrent.futures import ThreadPoolExecutor
import perspective.handlers.tornado as psp_tornado

def make_app(perspective_manager) -> tornado.web.Application:
    executor = ThreadPoolExecutor(max_workers=8)
    return tornado.web.Application([
        (
            r"/websocket",
            psp_tornado.PerspectiveTornadoHandler,
            {
                "perspective_server": perspective_manager.get_server(),
                "executor": executor,
            },
        ),
    ])
```

The `executor` ensures that inbound session requests (view reconfiguration, sorts, filters
from 50 traders) are processed on a thread pool rather than blocking the IOLoop.

---

## Main Entry Point (`server.py`)

Wire everything together and start the server.

### Startup sequence

1. Load `Settings` from `.env`
2. Configure logging
3. Create `PerspectiveManager`
4. Get the Tornado `IOLoop`
5. Create `FeedAdapter(perspective_manager, loop, settings.feed_flush_interval_ms)`
6. Call `start_receiver(settings, feed_adapter)` — starts Solace subscription
7. Create Tornado app via `make_app(perspective_manager)`
8. `app.listen(settings.perspective_port)`
9. Log startup banner
10. `loop.start()`

### Startup banner (log at INFO level)

```
=========================================
  FX Executions Blotter Server
  Port      : 8080
  Table     : fx_executions (limit: 200000 rows)
  Solace    : tcps://broker:55443
  Queue     : fx.executions.blotter
  Flush     : 50ms batch window
=========================================
```

### Graceful shutdown

Register `signal.SIGINT` and `signal.SIGTERM` handlers that:
1. Stop the Solace receiver (stop accepting new messages)
2. Stop the Tornado IOLoop cleanly
3. Log `"Server shutdown complete"`

---

## Tests

### `tests/test_feed_adapter.py`

- Test that `on_message` with valid JSON enqueues a row
- Test that `on_message` with invalid JSON logs a warning and does NOT enqueue
- Test that `_flush` calls `perspective_manager.update()` with the accumulated rows
- Test that after flush `_pending` is empty and `_flush_scheduled` is False
- Use `unittest.mock.MagicMock` for `perspective_manager` and `IOLoop`

### `tests/test_perspective_manager.py`

- Test that `PerspectiveManager.__init__` creates a table with the correct schema
- Test that `update([])` (empty list) does NOT call `table.update()`
- Test that `update([row])` calls `table.update()` once with the correct data

### `tests/fixtures/sample_execution.json`

Provide a valid JSON string matching the `FxExecution` schema for use in tests:

```json
{
  "trade_id": "T-20240314-001",
  "ccy_pair": "EUR/USD",
  "side": "BUY",
  "notional": 1000000.0,
  "rate": 1.082350,
  "venue": "EBS",
  "trader_id": "TR001",
  "desk": "EMEA_SPOT",
  "status": "FILLED",
  "exec_time": "2024-03-14T09:30:01.123Z",
  "value_date": "2024-03-16",
  "counterparty": "JPMORGAN",
  "pnl": 1250.50,
  "spot_rate": 1.082300,
  "sequence_num": 1
}
```

---

## Running the Server

```bash
# 1. Activate venv
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux / macOS

# 2. Copy and fill in environment variables
copy .env.example .env           # Windows
cp .env.example .env             # Linux

# 3. Edit .env with your Solace broker details

# 4. Start the server
python server.py

# 5. Connect a browser client to:
#    ws://localhost:8080/websocket
```

---

## Connecting a Browser Client

From any HTML page or Angular component, connect to the server:

```javascript
import perspective from "@finos/perspective";

const websocket = await perspective.websocket("ws://localhost:8080/websocket");
const table = await websocket.open_table("fx_executions");

const viewer = document.querySelector("perspective-viewer");
await viewer.load(table);
```

The viewer will receive live delta updates automatically every time the Solace feed
delivers new executions. No polling, no REST calls — pure WebSocket streaming.

---

## Performance Notes

- **50 traders × 4 updates/sec = 200 WebSocket writes/sec** — well within Tornado's capacity
- The 50ms flush window means at most 20 `table.update()` calls per second regardless of
  message burst rate from Solace
- The Perspective C++ engine releases the GIL during `table.update()` — the Tornado IOLoop
  remains responsive during heavy ingest bursts
- The `ThreadPoolExecutor(max_workers=8)` on the handler ensures view reconfigurations
  (trader changes sort/filter) don't block the IOLoop

---

## Key Constraints

- Do **not** call `table.update()` directly from the Solace `on_message` callback —
  always bridge via `IOLoop.add_callback()`
- Do **not** use `perspective.GLOBAL_SERVER` — always instantiate `perspective.Server()`
  explicitly (required in 4.x)
- The table name `"fx_executions"` must match exactly what the JavaScript client uses in
  `websocket.open_table("fx_executions")`
- Use `Queue.durable_exclusively_shared_queue()` not a topic subscription — this ensures
  no messages are lost during server restart
- Solace `receive_async()` is **not** asyncio-compatible — it uses native threads

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Solace connection fails at startup | Raise exception with clear message — do not start Tornado |
| Solace disconnects mid-session | API auto-reconnects — log warning, continue serving cached data |
| Malformed execution message | Log warning with raw payload, skip row, ack message |
| Perspective `table.update()` fails | Log error with row data, continue — do not crash server |
| Client WebSocket disconnects | Perspective handles session cleanup automatically |
| 50ms flush fires with empty pending | No-op — do not call `table.update()` |
