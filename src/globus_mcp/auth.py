import os

import globus_sdk

DEFAULT_CLIENT_ID = "f2a9c08a-4a6c-4524-936f-a4ec4fabb9bd"


def _get_client_creds() -> tuple[str | None, str | None]:
    client_id = os.getenv("GLOBUS_CLIENT_ID")
    client_secret = os.getenv("GLOBUS_CLIENT_SECRET")
    return client_id, client_secret


def get_globus_app() -> globus_sdk.GlobusApp:
    app_name = "Globus MCP Server"
    client_id, client_secret = _get_client_creds()

    if client_id and client_secret:
        return globus_sdk.ClientApp(
            app_name=app_name, client_id=client_id, client_secret=client_secret
        )

    elif client_secret:
        raise ValueError("GLOBUS_CLIENT_SECRET requires GLOBUS_CLIENT_ID to be set")

    else:
        client_id = client_id or DEFAULT_CLIENT_ID
        config = globus_sdk.GlobusAppConfig(login_flow_manager="local-server")
        return globus_sdk.UserApp(app_name=app_name, client_id=client_id, config=config)
