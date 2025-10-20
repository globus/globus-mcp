from pydantic import BaseModel, Field, JsonValue


class ComputeEndpoint(BaseModel):
    endpoint_id: str = Field(description="ID of the endpoint")
    name: str = Field(description="The endpoint name")
    display_name: str = Field(description="Friendly name for the endpoint")
    owner_id: str = Field(description="ID of the endpoint owner")


class ComputeFunctionRegisterResponse(BaseModel):
    function_id: str = Field(description="ID of the registered function")


class ComputeSubmitResponse(BaseModel):
    task_id: str = Field(description="ID of the task")


class ComputeTask(BaseModel):
    task_id: str = Field(description="ID of the task")
    status: str = Field(description="The status of the task.")
    result: JsonValue = Field(
        description="When the task status is 'success', this will contain the task result.",
    )
    exception: str | None = Field(
        default=None,
        description="When the task status is 'failed', this will contain the exception traceback.",
    )
