from typing import Literal

from pydantic import BaseModel, Field


class WhoAmI(BaseModel):
    identity_id: str = Field(description="The Globus identity ID used by this server.")
    identity_type: Literal["user", "client"] = Field(
        description="Whether requests are made as a human user or a service account"
    )
    username: str = Field(description="The Globus username")
    name: str = Field(description="The display name of the user or client, if known.")

    identity_provider_display_name: str = Field(
        description="The identity provider used to authenticate"
    )
    organization: str | None = Field()
