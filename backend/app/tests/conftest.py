"""Isolate API tests on an injected in-memory MongoDB client."""
from contextlib import contextmanager

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import clear_store_caches, ensure_indexes, get_control_store
from app.core.docstore import DocStore
from app.core.mongo import set_mongo_client
from app.seeds.seed_demo import run_seed


@pytest.fixture(autouse=True)
def isolated_mongo_store(monkeypatch):
    """Install mongomock and seed demo data before any API request or startup hook."""
    @contextmanager
    def no_mock_transaction(self):
        yield self

    # mongomock does not implement PyMongo sessions. Production request scopes
    # and explicit route transactions remain untouched outside these tests.
    monkeypatch.setattr(DocStore, "request_scope", no_mock_transaction)
    monkeypatch.setattr(DocStore, "transaction", no_mock_transaction)

    client = mongomock.MongoClient(tz_aware=True)
    set_mongo_client(client)
    clear_store_caches()
    store = get_control_store()
    ensure_indexes(store)
    run_seed(store)

    try:
        # Exercise the real app startup hook with the injected client already set.
        with TestClient(app):
            yield store
    finally:
        clear_store_caches()
        set_mongo_client(None)
