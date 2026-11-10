import os

import pytest
import responses


@pytest.fixture(autouse=True)
def mocked_responses(monkeypatch):
    """
    Enable testing globus SDK calls with synthetic payloads. Register fake replies with
    `globus_sdk.testing.load_response`.
    """
    responses.start()
    monkeypatch.setitem(os.environ, "GLOBUS_SDK_ENVIRONMENT", "production")
    yield
    responses.stop()
    responses.reset()
