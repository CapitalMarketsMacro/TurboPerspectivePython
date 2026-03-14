import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

log = logging.getLogger(__name__)

FX_SCHEMA = {
    "trade_id": str,
    "ccy_pair": str,
    "side": str,
    "notional": float,
    "rate": float,
    "venue": str,
    "trader_id": str,
    "desk": str,
    "status": str,
    "exec_time": "datetime",
    "value_date": "date",
    "counterparty": str,
    "pnl": float,
    "spot_rate": float,
    "sequence_num": int,
}

_STRING_DEFAULTS = {
    "ccy_pair": "",
    "side": "",
    "venue": "",
    "trader_id": "",
    "desk": "",
    "status": "",
    "counterparty": "",
}

_FLOAT_DEFAULTS = {
    "notional": 0.0,
    "rate": 0.0,
    "pnl": 0.0,
    "spot_rate": 0.0,
}


@dataclass
class FxExecution:
    trade_id: str
    ccy_pair: str
    side: str
    notional: float
    rate: float
    venue: str
    trader_id: str
    desk: str
    status: str
    exec_time: str
    value_date: str
    counterparty: str
    pnl: float
    spot_rate: float
    sequence_num: int


def _parse_exec_time(value) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return str(value)
    except (ValueError, TypeError):
        log.warning("Unparseable exec_time '%s', defaulting to current UTC", value)
        return datetime.now(timezone.utc).isoformat()


def parse_execution(raw: bytes | str) -> dict:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")

    data = json.loads(raw)

    trade_id = data.get("trade_id")
    if not trade_id:
        raise ValueError("trade_id is required")

    row = {"trade_id": str(trade_id)}

    for field, default in _STRING_DEFAULTS.items():
        row[field] = str(data.get(field, default)) if data.get(field) is not None else default

    for field, default in _FLOAT_DEFAULTS.items():
        try:
            row[field] = float(data.get(field, default))
        except (ValueError, TypeError):
            row[field] = default

    row["exec_time"] = _parse_exec_time(data.get("exec_time"))
    row["value_date"] = str(data.get("value_date", "")) if data.get("value_date") else ""

    try:
        row["sequence_num"] = int(data.get("sequence_num", 0))
    except (ValueError, TypeError):
        row["sequence_num"] = 0

    return row
