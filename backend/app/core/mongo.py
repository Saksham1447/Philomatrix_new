"""Process-wide synchronous PyMongo client management."""
from threading import RLock
from datetime import timezone
from typing import Any

from pymongo import MongoClient

from app.core.config import settings

_lock = RLock()
_client: Any | None = None


def get_mongo_client():
    """Return the process-wide client without logging or exposing its URI."""
    global _client
    with _lock:
        if _client is None:
            uri = settings.MONGODB_URI
            if not uri:
                raise RuntimeError("MONGODB_URI is required to connect to MongoDB; inject a test client in tests")
            _client = MongoClient(
                uri,
                tz_aware=True,
                tzinfo=timezone.utc,
                uuidRepresentation="standard",
                serverSelectionTimeoutMS=5000,
            )
        return _client


def set_mongo_client(client: Any | None) -> None:
    """Install an explicitly supplied client (used by tests); None restores lazy production setup."""
    global _client
    with _lock:
        if _client is not None and _client is not client:
            try:
                _client.close()
            except Exception:
                pass
        _client = client


def close_mongo_client() -> None:
    global _client
    with _lock:
        if _client is not None:
            _client.close()
            _client = None
