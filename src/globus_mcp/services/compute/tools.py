from collections.abc import Callable
from typing import Annotated, Any, Literal

import globus_sdk
from globus_compute_sdk.serialize import JSONData
from globus_compute_sdk.serialize.facade import validate_strategylike
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.session import ServerSession
from pydantic import Field

from globus_mcp.context import GlobusContext
from globus_mcp.services.compute.client import get_compute_client
from globus_mcp.services.compute.schemas import (
    ComputeEndpoint,
    ComputeFunctionRegisterResponse,
    ComputeSubmitResponse,
    ComputeTask,
)


def globus_compute_list_endpoints(
    role: Annotated[
        Literal["any", "owner"],
        Field(
            default="any",
            description=(
                "Filter returned list by the user's association to endpoints."
                " Specify 'any' (default) to return all endpoints that the user"
                " can submit tasks to. Specify 'owner' to only return endpoints"
                " that the user owns."
            ),
        ),
    ],
    ctx: Context[ServerSession, GlobusContext],
) -> list[ComputeEndpoint]:
    """List Globus Compute endpoints that the user has access to."""
    client = get_compute_client(ctx)

    try:
        res = client.get_endpoints(role=role)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to get endpoints: {e}") from e

    endpoints = []
    for ep in res:
        endpoint = ComputeEndpoint(
            endpoint_id=ep["uuid"],
            name=ep["name"],
            display_name=ep["display_name"],
            owner_id=ep["owner"],
        )
        endpoints.append(endpoint)

    return endpoints


def globus_compute_register_python_function(
    function_code: Annotated[str, Field(description="The text of the Python function source code")],
    function_name: Annotated[str, Field(description="The name of the Python function")],
    description: Annotated[
        str | None,
        Field(default=None, description="An optional description of the Python function"),
    ],
    public: Annotated[
        bool,
        Field(
            description="Indicates whether the Python function can be used by others",
            default=False,
        ),
    ],
    ctx: Context[ServerSession, GlobusContext],
) -> ComputeFunctionRegisterResponse:
    """Register a Python function with Globus Compute.

    Use globus_compute_submit_task to run the registered Python function on an endpoint.
    """
    client = get_compute_client(ctx)

    try:
        function_id = client.register_source_code(
            source=function_code,
            function_name=function_name,
            description=description,
            public=public,
        )
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to register Python function: {e}") from e

    return ComputeFunctionRegisterResponse(function_id=function_id)


_SHELL_FUNCTION_TEMPLATE = """
def {function_name}(*args, **kwargs):
    import subprocess
    try:
        completed = subprocess.run(
            '''{command}'''.format(*args, **kwargs),
            shell=True,
            capture_output=True,
            text=True,
            timeout={timeout},
        )
        return {{
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }}
    except subprocess.TimeoutExpired:
        return {{
            "returncode": -1,
            "stdout": "",
            "stderr": "Command timed out after {timeout} seconds",
        }}
"""


def globus_compute_register_shell_command(
    command: Annotated[
        str,
        Field(
            description=(
                "The shell command string, which may contain variables to be replaced with"
                " args and kwargs provided in each submit call (e.g.`echo {} --foo {foo}`)."
            )
        ),
    ],
    timeout: Annotated[
        float | None,
        Field(default=None, description="Maximum execution time in seconds."),
    ],
    description: Annotated[
        str | None,
        Field(default=None, description="An optional description of the shell command"),
    ],
    public: Annotated[
        bool,
        Field(
            description="Indicates whether the shell command can be used by others",
            default=False,
        ),
    ],
    ctx: Context[ServerSession, GlobusContext],
) -> ComputeFunctionRegisterResponse:
    """Register a shell command function with Globus Compute.

    Use globus_compute_submit_task to run the registered shell command on an endpoint.
    """
    client = get_compute_client(ctx)

    function_name = "run_shell_command"
    source = _SHELL_FUNCTION_TEMPLATE.format(
        function_name=function_name, command=command, timeout=timeout
    )

    try:
        function_id = client.register_source_code(
            source=source,
            function_name=function_name,
            description=description,
            public=public,
        )
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to register shell command: {e}") from e

    return ComputeFunctionRegisterResponse(function_id=function_id)


def globus_compute_submit_task(
    endpoint_id: Annotated[
        str, Field(description="ID of the endpoint that will execute the function")
    ],
    function_id: Annotated[str, Field(description="ID of the function")],
    function_args: Annotated[
        tuple[Any, ...] | None,
        Field(description="Positional arguments for the function"),
    ],
    function_kwargs: Annotated[
        dict[str, Any] | None, Field(description="Keyword arguments for the function")
    ],
    ctx: Context[ServerSession, GlobusContext],
) -> ComputeSubmitResponse:
    """Submit a function execution task to a Globus Compute endpoint.

    Use globus_compute_get_task_status to monitor progress and retrieve results.
    """
    client = get_compute_client(ctx)

    batch = client.create_batch(result_serializers=[validate_strategylike(JSONData).import_path])
    batch.add(function_id, function_args, function_kwargs)

    try:
        res = client.batch_run(endpoint_id, batch)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to submit task: {e}") from e

    task_id = res["tasks"][function_id][0]
    return ComputeSubmitResponse(task_id=task_id)


def globus_compute_get_task_status(
    task_id: Annotated[str, Field(description="The ID of the task")],
    ctx: Context[ServerSession, GlobusContext],
) -> ComputeTask:
    """Retrieve the status and result of a Globus Compute task."""
    client = get_compute_client(ctx)

    try:
        res = client._compute_web_client.v2.get_task(task_id)
    except globus_sdk.GlobusAPIError as e:
        raise ToolError(f"Failed to get task status: {e}") from e

    result = res.get("result")
    if result:
        try:
            result = client.fx_serializer.deserialize(result)
        except Exception as e:
            raise ToolError("Unable to deserialize result") from e

    return ComputeTask(
        task_id=res["task_id"],
        status=res.get("status"),
        result=result,
        exception=res.get("exception"),
    )


ALL_COMPUTE_TOOLS: list[Callable[..., Any]] = [
    globus_compute_list_endpoints,
    globus_compute_register_python_function,
    globus_compute_register_shell_command,
    globus_compute_submit_task,
    globus_compute_get_task_status,
]
