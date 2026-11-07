from unittest.mock import Mock

import pytest
from globus_sdk import ClientApp, GlobusApp, UserApp
from globus_sdk.testing import RegisteredResponse, load_response
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError

from globus_mcp.context import GlobusContext
from globus_mcp.services.auth.tools import globus_auth_userinfo

USERINFO_PATH = "/v2/oauth2/userinfo"


def make_ctx(app: GlobusApp, auth_client) -> Mock:
    ctx = Mock(spec=Context)
    ctx.request_context.lifespan_context = GlobusContext(app=app, auth_client=auth_client)
    return ctx


def test_user_app(auth_client):
    load_response(
        RegisteredResponse(
            service="auth",
            method="GET",
            path=USERINFO_PATH,
            json={
                "email": "tess.ting@acme.example",
                "identity_provider": "00000000-0000-0000-0000-000000000000",
                "identity_provider_display_name": "Acme Inc",
                "identity_set": [
                    {
                        "email": "tess.ting@acme.example",
                        "identity_provider": "00000000-0000-0000-0000-000000000000",
                        "identity_provider_display_name": "Acme Inc",
                        "last_authentication": 1,
                        "name": "Tess Ting",
                        "organization": "Acme Inc",
                        "sub": "10000000-0000-0000-0000-000000000000",
                        "username": "tess.ting@acme.example",
                    }
                ],
                "last_authentication": 1,
                "name": "Tess Ting",
                "organization": "Acme Inc",
                "preferred_username": "tess.ting@acme.example",
                "sub": "10000000-0000-0000-0000-000000000000",
            },
        )
    )

    ctx = make_ctx(UserApp("test-app", client_id="aaaaa"), auth_client)
    res = globus_auth_userinfo(ctx=ctx)

    assert res.identity_id == "10000000-0000-0000-0000-000000000000"
    assert res.identity_type == "user"
    assert res.username == "tess.ting@acme.example"
    assert res.name == "Tess Ting"
    assert res.identity_provider_display_name == "Acme Inc"
    assert res.organization == "Acme Inc"


def test_client_app(auth_client):
    CLIENT_ID = "20000000-0000-0000-0000-000000000000"
    CLIENT_IDP = "30000000-0000-0000-0000-000000000000"
    CLIENT_USERNAME = f"{CLIENT_ID}@clients.auth.globus.org"

    load_response(
        RegisteredResponse(
            service="auth",
            method="GET",
            path=USERINFO_PATH,
            json={
                "email": None,
                "identity_provider": CLIENT_IDP,
                "identity_provider_display_name": "Globus Auth",
                "identity_set": [
                    {
                        "email": None,
                        "identity_provider": CLIENT_IDP,
                        "identity_provider_display_name": "Globus Auth",
                        "last_authentication": None,
                        "name": "Test ClientApp identity",
                        "sub": CLIENT_ID,
                        "username": CLIENT_USERNAME,
                    }
                ],
                "last_authentication": None,
                "name": "Test ClientApp identity",
                "preferred_username": CLIENT_USERNAME,
                "sub": CLIENT_ID,
            },
        )
    )

    app = ClientApp("test-app", client_id="aaaaa", client_secret="bbbbb")
    res = globus_auth_userinfo(ctx=make_ctx(app, auth_client))

    assert res.identity_id == CLIENT_ID
    assert res.identity_type == "client"
    assert res.username == CLIENT_USERNAME
    assert res.name == "Test ClientApp identity"
    assert res.identity_provider_display_name == "Globus Auth"
    assert res.organization is None


def test_user_app_invalid_login(auth_client):
    load_response("auth.userinfo", case="unauthorized")

    app = UserApp("test-app", client_id="aaaaa")
    with pytest.raises(ToolError, match=r"HTTP 401: Invalid user login"):
        globus_auth_userinfo(ctx=make_ctx(app, auth_client))


def test_client_app_invalid_credentials(auth_client):
    load_response("auth.userinfo", case="unauthorized")

    app = ClientApp("test-app", client_id="aaaaa", client_secret="bbbbb")
    with pytest.raises(ToolError, match=r"HTTP 401: Invalid client credentials"):
        globus_auth_userinfo(ctx=make_ctx(app, auth_client))


def test_other_api_error(auth_client):
    # Any non-401 API error falls back to the generic message
    load_response("auth.userinfo", case="forbidden")

    app = UserApp("test-app", client_id="aaaaa")
    with pytest.raises(ToolError, match=r"Failed to get identity information"):
        globus_auth_userinfo(ctx=make_ctx(app, auth_client))
