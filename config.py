import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

_SOLACE_REQUIRED = [
    "SOLACE_HOST",
    "SOLACE_VPN",
    "SOLACE_USERNAME",
    "SOLACE_PASSWORD",
    "SOLACE_TOPIC",
]

_NATS_REQUIRED = [
    "NATS_URL",
    "NATS_SUBJECT",
]


@dataclass
class Settings:
    # Feed source: "solace" or "nats"
    feed_source: str

    # Solace settings
    solace_host: str = ""
    solace_vpn: str = ""
    solace_username: str = ""
    solace_password: str = ""
    solace_topic: str = ""

    # NATS settings
    nats_url: str = ""
    nats_creds_file: str = ""
    nats_subject: str = ""

    # Shared settings
    perspective_port: int = 8080
    feed_flush_interval_ms: int = 50
    perspective_table_limit: int = 200_000
    log_level: str = "INFO"


def load_settings(feed_source: str = "solace") -> Settings:
    feed_source = feed_source.lower()
    if feed_source not in ("solace", "nats"):
        raise ValueError(f"Invalid feed source '{feed_source}'. Must be 'solace' or 'nats'.")

    if feed_source == "solace":
        required = _SOLACE_REQUIRED
    else:
        required = _NATS_REQUIRED

    missing = [v for v in required if not os.environ.get(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables for {feed_source}: {', '.join(missing)}"
        )

    return Settings(
        feed_source=feed_source,
        # Solace
        solace_host=os.environ.get("SOLACE_HOST", ""),
        solace_vpn=os.environ.get("SOLACE_VPN", ""),
        solace_username=os.environ.get("SOLACE_USERNAME", ""),
        solace_password=os.environ.get("SOLACE_PASSWORD", ""),
        solace_topic=os.environ.get("SOLACE_TOPIC", ""),
        # NATS
        nats_url=os.environ.get("NATS_URL", ""),
        nats_creds_file=os.environ.get("NATS_CREDS_FILE", ""),
        nats_subject=os.environ.get("NATS_SUBJECT", ""),
        # Shared
        perspective_port=int(os.environ.get("PERSPECTIVE_PORT", "8080")),
        feed_flush_interval_ms=int(os.environ.get("FEED_FLUSH_INTERVAL_MS", "50")),
        perspective_table_limit=int(os.environ.get("PERSPECTIVE_TABLE_LIMIT", "200000")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
