import uuid

import pytest
from globus_sdk import ClientApp, UserApp
from pytest import MonkeyPatch

from globus_mcp.auth import DEFAULT_CLIENT_ID, get_globus_app
from tests.utils import random_string


def test_get_globus_app_default():
    app = get_globus_app()
    assert isinstance(app, UserApp)
    assert app.client_id == DEFAULT_CLIENT_ID
    assert app.config.login_flow_manager == "local-server"
    assert app.app_name == "Globus MCP Server"


def test_get_globus_app_custom_client_id(monkeypatch: MonkeyPatch):
    client_id = str(uuid.uuid4())
    monkeypatch.setenv("GLOBUS_CLIENT_ID", client_id)
    app = get_globus_app()
    assert isinstance(app, UserApp)
    assert app.client_id == client_id


def test_get_globus_app_custom_client_id_and_secret(monkeypatch: MonkeyPatch):
    client_id = str(uuid.uuid4())
    client_secret = random_string()
    monkeypatch.setenv("GLOBUS_CLIENT_ID", client_id)
    monkeypatch.setenv("GLOBUS_CLIENT_SECRET", client_secret)
    app = get_globus_app()
    assert isinstance(app, ClientApp)
    assert app.client_id == client_id


def test_get_globus_app_missing_client_id(monkeypatch: MonkeyPatch):
    client_secret = random_string()
    monkeypatch.setenv("GLOBUS_CLIENT_SECRET", client_secret)
    with pytest.raises(ValueError) as exc_info:
        get_globus_app()
    assert "requires GLOBUS_CLIENT_ID" in str(exc_info.value)
