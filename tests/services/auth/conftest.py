import os
from collections.abc import Iterator

import pytest
import responses
from globus_sdk import AuthClient


@pytest.fixture(autouse=True)
def mocked_responses(monkeypatch):
    responses.start()
    monkeypatch.setitem(os.environ, "GLOBUS_SDK_ENVIRONMENT", "production")
    yield
    responses.stop()
    responses.reset()


@pytest.fixture
def auth_client() -> Iterator[AuthClient]:
    client = AuthClient()
    with client.retry_config.tune(max_retries=0):
        yield client
